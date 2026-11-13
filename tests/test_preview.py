import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'templates/interactive-preview.html'
needs_node = pytest.mark.skipif(shutil.which('node') is None, reason='Scenario replay requires node')


def run(path, *flags):
    return subprocess.run([sys.executable, str(ROOT / 'scripts/check_preview.py'), str(path), *flags],
                          capture_output=True, text=True, encoding='utf-8')


def make(tmp_path, *, data=None, html=None, doc=None):
    """在临时目录生成一份预演及其主案；data 回调修改数据块，html 回调修改整页。"""
    source = tmp_path / 'main.md'
    source.write_text(doc or (ROOT / 'tests/fixtures/small-requirement.md').read_text(encoding='utf-8'), encoding='utf-8')
    text = TEMPLATE.read_text(encoding='utf-8')
    block = re.search(r'(<script[^>]*id="preview-data"[^>]*>)(.*?)(</script>)', text, flags=re.S)
    payload = json.loads(block.group(2))
    payload['meta']['source'] = 'main.md'
    if data:
        data(payload)
    text = text[:block.start(2)] + '\n' + json.dumps(payload, ensure_ascii=False, indent=1) + '\n' + text[block.end(2):]
    if html:
        text = html(text)
    preview = tmp_path / 'preview.html'
    preview.write_text(text, encoding='utf-8')
    return preview


@needs_node
def test_template_and_generated_copy_pass():
    assert run(TEMPLATE).returncode == 0


@needs_node
def test_copy_of_template_passes(tmp_path):
    result = run(make(tmp_path))
    assert result.returncode == 0, result.stdout


def test_external_resource_is_rejected(tmp_path):
    preview = make(tmp_path, html=lambda t: t.replace('</head>', '<script src="https://cdn.example.com/x.js"></script></head>'))
    result = run(preview, '--static')
    assert result.returncode == 1 and '外部资源' in result.stdout


def test_rule_must_point_to_existing_heading(tmp_path):
    def mutate(d): d['rules'][0]['section'] = '不存在的章节'
    result = run(make(tmp_path, data=mutate), '--static')
    assert result.returncode == 1 and 'R1 引用的章节在主案中不存在' in result.stdout


def test_stale_source_version_is_rejected(tmp_path):
    doc = (ROOT / 'tests/fixtures/small-requirement.md').read_text(encoding='utf-8')
    doc = doc.replace('| v1.0 | 新建 |', '| v1.1 | 修改 | 调整取消规则 | 示例 | 2026-10-01 |\n| v1.0 | 新建 |')
    result = run(make(tmp_path, doc=doc), '--static')
    assert result.returncode == 1 and '主案已是 v1.1' in result.stdout


def test_every_rule_needs_a_scenario(tmp_path):
    def mutate(d): d['scenarios'] = [s for s in d['scenarios'] if s['id'] != 'S3']
    result = run(make(tmp_path, data=mutate), '--static')
    assert result.returncode == 1 and '规则 R4 没有任何场景覆盖' in result.stdout


def test_param_origin_is_required(tmp_path):
    def mutate(d): d['params'][0].pop('origin')
    result = run(make(tmp_path, data=mutate), '--static')
    assert result.returncode == 1 and 'origin' in result.stdout


def test_open_gap_blocks_unless_allowed(tmp_path):
    def mutate(d): d['gaps'] = [{'id': 'G1', 'question': '关闭后是否刷新选择', 'where': '确认弹窗', 'status': 'open'}]
    preview = make(tmp_path, data=mutate)
    assert run(preview, '--static').returncode == 1
    allowed = run(preview, '--static', '--allow-open-gaps')
    assert allowed.returncode == 0 and '待定细节 G1' in allowed.stdout and '回放未执行' in allowed.stdout


def test_resolved_gap_must_be_removed(tmp_path):
    def mutate(d): d['gaps'] = [{'id': 'G1', 'question': 'x', 'where': 'y', 'status': 'resolved'}]
    result = run(make(tmp_path, data=mutate), '--static', '--allow-open-gaps')
    assert result.returncode == 1 and '回写主案' in result.stdout


def test_modified_engine_is_rejected(tmp_path):
    preview = make(tmp_path, html=lambda t: t.replace("st.toast = null;\n    st.log.push({t: 'act'", "st.log.push({t: 'act'"))
    result = run(preview, '--static')
    assert result.returncode == 1 and '引擎与' in result.stdout


@needs_node
def test_replay_catches_wrong_expectation(tmp_path):
    def mutate(d): d['scenarios'][1]['expect']['hits'] = ['R1', 'R2']
    result = run(make(tmp_path, data=mutate))
    assert result.returncode == 1 and 'S2 命中规则不符' in result.stdout


@needs_node
def test_replay_catches_flow_calling_unknown_rule(tmp_path):
    preview = make(tmp_path, html=lambda t: t.replace("c.hit('R4');", "c.hit('R9');"))
    result = run(preview)
    assert result.returncode == 1 and '未登记的规则：R9' in result.stdout


def test_open_only_after_checks_pass(tmp_path, monkeypatch, capsys):
    sys.path.insert(0, str(ROOT / 'scripts'))
    import check_preview
    opened = []
    monkeypatch.setattr(check_preview.webbrowser, 'open', lambda url: opened.append(url) or True)
    good = make(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['check_preview.py', str(good), '--static', '--open'])
    assert check_preview.main() == 0
    assert opened == [good.resolve().as_uri()]
    bad = make(tmp_path, data=lambda d: d['rules'][0].update(section='不存在的章节'))
    monkeypatch.setattr(sys, 'argv', ['check_preview.py', str(bad), '--static', '--open'])
    assert check_preview.main() == 1
    assert len(opened) == 1


PNG_1PX = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360606060000000050001a5f645400000000049454e44ae426082')


def export_dir(tmp_path):
    layers = tmp_path / 'layers'; layers.mkdir()
    (layers / 'panel.png').write_bytes(PNG_1PX)
    (layers / 'panel.json').write_text(json.dumps({
        'name': 'panel', 'prefab': 'Assets/UI/Panel.prefab', 'image': 'panel.png', 'x': 0, 'y': 0, 'w': 1080, 'h': 1920,
        'hotspots': {'ok': {'x': 100, 'y': 200, 'w': 300, 'h': 120}},
        'slots': {'tip': {'x': 10, 'y': 20, 'w': 200, 'h': 40, 'pivot': 0.5, 'fontSize': 28, 'color': '#FFFFFF'}}}), encoding='utf-8')
    return layers


def embed(layers, preview):
    return subprocess.run([sys.executable, str(ROOT / 'scripts/build_preview_ui.py'), str(layers), str(preview)],
                          capture_output=True, text=True, encoding='utf-8')


UI_FLOW = """
Preview.define({
  initial: 'select',
  screens: {select: {render: function (c) { return c.layer('panel', {slots: {tip: 'x'}, acts: {ok: {act: 'submit', label: '提交'}}}); }}},
  modals: {confirm: {render: function (c) { return c.note(0, 0, 400, '确认', '示意', {act: 'confirm'}) + c.note(0, 300, 400, '取消', '示意', {act: 'cancel'}); }}},
  actions: {
    submit: function (c) { c.hit('R1'); c.open('confirm'); },
    confirm: function (c) { c.close(); c.hit(c.p.valid ? 'R2' : 'R3'); },
    cancel: function (c) { c.close(); c.hit('R4'); }
  }
});
"""


def with_ui_flow(text, flow=UI_FLOW):
    block = re.search(r'(<script id="preview-flow">)(.*?)(</script>)', text, flags=re.S)
    return text[:block.start(2)] + flow + text[block.end(2):]


@needs_node
def test_embedded_ui_layers_render_and_replay(tmp_path):
    preview = make(tmp_path, html=with_ui_flow)
    result = embed(export_dir(tmp_path), preview)
    assert result.returncode == 0, result.stdout
    html = preview.read_text(encoding='utf-8')
    assert html.count('id="preview-ui"') == 1 and 'data:image/png;base64,' in html
    assert run(preview).returncode == 0, run(preview).stdout
    # 重复写入只替换，不追加
    assert embed(tmp_path / 'layers', preview).returncode == 0
    assert preview.read_text(encoding='utf-8').count('id="preview-ui"') == 1


@needs_node
def test_flow_referencing_missing_layer_or_hotspot_is_rejected(tmp_path):
    preview = make(tmp_path, html=lambda t: with_ui_flow(t, UI_FLOW.replace("acts: {ok:", "acts: {missing:")))
    assert embed(export_dir(tmp_path), preview).returncode == 0
    result = run(preview)
    assert result.returncode == 1 and '没有热区：missing' in result.stdout


def test_ui_layer_must_record_source_prefab(tmp_path):
    preview = make(tmp_path)
    layers = export_dir(tmp_path)
    meta = json.loads((layers / 'panel.json').read_text(encoding='utf-8')); meta['prefab'] = ''
    (layers / 'panel.json').write_text(json.dumps(meta), encoding='utf-8')
    assert embed(layers, preview).returncode == 0
    result = run(preview, '--static')
    assert result.returncode == 1 and '没有记录来源 prefab' in result.stdout


def test_embed_accepts_several_sources_and_single_layer_files(tmp_path):
    preview = make(tmp_path)
    layers = export_dir(tmp_path)
    lib = tmp_path / 'lib'; lib.mkdir()
    (lib / 'box.png').write_bytes(PNG_1PX)
    (lib / 'other.png').write_bytes(PNG_1PX)
    for name in ('box', 'other'):
        (lib / f'{name}.json').write_text(json.dumps({'name': name, 'prefab': 'Assets/UI/Box.prefab', 'image': f'{name}.png',
                                                    'x': 0, 'y': 0, 'w': 10, 'h': 10}), encoding='utf-8')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build_preview_ui.py'), str(layers), str(lib / 'box.json'), str(preview)],
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout
    ui = json.loads(re.search(r'id="preview-ui">(.*?)</script>', preview.read_text(encoding='utf-8'), flags=re.S).group(1))
    assert sorted(ui['layers']) == ['box', 'panel']
    # 同名图层来自两个来源时拒绝，避免悄悄覆盖
    clash = subprocess.run([sys.executable, str(ROOT / 'scripts/build_preview_ui.py'), str(lib), str(lib / 'box.json'), str(preview)],
                           capture_output=True, text=True, encoding='utf-8')
    assert clash.returncode == 1 and '图层重名' in clash.stdout


@needs_node
def test_wrapped_slot_passes_replay(tmp_path):
    preview = make(tmp_path, html=with_ui_flow)
    layers = export_dir(tmp_path)
    meta = json.loads((layers / 'panel.json').read_text(encoding='utf-8'))
    meta['slots']['tip'].update(wrap=True, align='UpperLeft')
    (layers / 'panel.json').write_text(json.dumps(meta), encoding='utf-8')
    assert embed(layers, preview).returncode == 0
    assert run(preview).returncode == 0, run(preview).stdout


def library(tmp_path, exported=('box',)):
    lib = tmp_path / 'lib'; (lib / 'layers').mkdir(parents=True)
    spec = {'out': 'layers', 'layers': [{'name': 'box', 'prefab': 'Assets/UI/Box.prefab', 'slots': {'title': 'T'}, 'hotspots': {'ok': 'B'}}]}
    (lib / 'spec.json').write_text(json.dumps(spec), encoding='utf-8')
    for name in exported:
        (lib / 'layers' / f'{name}.png').write_bytes(PNG_1PX)
        (lib / 'layers' / f'{name}.json').write_text(json.dumps({
            'name': name, 'prefab': 'Assets/UI/Box.prefab', 'image': f'{name}.png', 'x': 0, 'y': 0, 'w': 10, 'h': 10,
            'slots': {'title': {}}, 'hotspots': {'ok': {}}}), encoding='utf-8')
    return lib


def ui_library(*args):
    return subprocess.run([sys.executable, str(ROOT / 'scripts/ui_library.py'), *map(str, args)], capture_output=True, text=True, encoding='utf-8')


def test_library_must_be_fetched_before_use(tmp_path):
    lib = library(tmp_path, exported=())
    status = ui_library('status', lib)
    assert status.returncode == 1 and '还没有获取' in status.stdout and 'prepare' in status.stdout
    assert ui_library('finish', lib).returncode == 1
    # 预演引用未获取的库图层时，报错里给出获取办法
    preview = make(tmp_path)
    missing = tmp_path / 'ui-library' / 'k1' / 'layers' / 'box.json'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build_preview_ui.py'), str(missing), str(preview)],
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 1 and 'ui_library.py status' in result.stdout


def test_library_finish_records_source_and_detects_stale_spec(tmp_path):
    lib = library(tmp_path)
    assert ui_library('status', lib).returncode == 1  # 已导出但未核对
    done = ui_library('finish', lib)
    assert done.returncode == 0, done.stdout
    assert (lib / 'layers' / 'README.md').is_file() and ui_library('status', lib).returncode == 0
    spec = json.loads((lib / 'spec.json').read_text(encoding='utf-8'))
    spec['layers'][0]['hotspots']['close'] = 'C'
    (lib / 'spec.json').write_text(json.dumps(spec), encoding='utf-8')
    stale = ui_library('status', lib)
    assert stale.returncode == 1 and '规格在上次导出后有改动' in stale.stdout
    lost = ui_library('finish', lib)
    assert lost.returncode == 1 and '热区没有导出：close' in lost.stdout


def test_library_spec_is_tracked_and_prepare_fills_spec_path(tmp_path):
    spec = json.loads((ROOT / 'ui-library/k1/spec.json').read_text(encoding='utf-8'))
    assert len({layer['name'] for layer in spec['layers']}) == len(spec['layers'])
    assert all(layer.get('title') and layer.get('prefab') for layer in spec['layers'])
    lib = library(tmp_path)
    out = ui_library('prepare', lib)
    assert out.returncode == 0, out.stdout
    code = Path(re.search(r'导出代码已生成：(.+)', out.stdout).group(1).strip()).read_text(encoding='utf-8')
    assert '__SPEC_PATH__' not in code and (lib / 'spec.json').resolve().as_posix() in code
