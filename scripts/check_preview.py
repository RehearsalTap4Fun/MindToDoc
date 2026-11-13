"""只读检查交互预演网页；退出 0 表示机械检查通过，不代表规则理解正确或界面观感合格。

检查：python scripts/check_preview.py output/<功能名>-交互预演.html
  --allow-open-gaps  评审中的预演允许保留未拍板的待定细节（仍会列出）
  --static           只做静态检查，不用 node 回放场景；此时输出会注明回放未执行
  --open             检查通过后用系统默认浏览器打开该网页；未通过时不打开

核对内容：单文件离线、引擎与模板一致、界面图层内嵌且有来源、规则引用的主案章节真实存在、
预演依据的版本是主案最新版本、每条规则至少被一个场景覆盖、逐场景回放结果与预期一致。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import webbrowser
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'templates/interactive-preview.html'
RUNNER = ROOT / 'scripts/preview_runner.cjs'
RESOURCE_TAGS = {'script', 'link', 'img', 'iframe', 'source', 'video', 'audio', 'embed', 'object'}
PARAM_TYPES = {'toggle', 'number', 'select'}


class Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag in RESOURCE_TAGS:
            self.items.extend((tag, value) for key, value in attrs if key in {'src', 'href', 'data'} and value)


def script_block(html: str, block_id: str) -> str | None:
    m = re.search(r'<script[^>]*\bid="%s"[^>]*>(.*?)</script>' % re.escape(block_id), html, flags=re.S)
    return m.group(1) if m else None


def headings_and_version(doc: Path) -> tuple[set[str], str | None]:
    """返回主案全部标题文本，以及变更记录中的最高版本号。"""
    headings, versions, fence = set(), [], False
    for line in doc.read_text(encoding='utf-8-sig').splitlines():
        s = line.strip()
        if re.match(r'^(`{3,}|~{3,})', s):
            fence = not fence
            continue
        if fence:
            continue
        m = re.match(r'^#{1,6}\s+(.+?)\s*#*$', s)
        if m:
            headings.add(m.group(1).strip())
        m = re.match(r'^\|\s*(v\d+(?:\.\d+)*)\s*\|', s)
        if m:
            versions.append(m.group(1))
    latest = max(versions, key=lambda v: tuple(int(x) for x in v[1:].split('.'))) if versions else None
    return headings, latest


def normalize(code: str) -> str:
    return re.sub(r'\s+', ' ', code).strip()


def check_preview(path: Path, *, allow_open_gaps=False, static=False) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    try:
        html = path.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError) as exc:
        return [f'无法读取：{exc}'], notes

    # 1. 单文件离线：不加载外部资源，本地资源必须存在。
    parser = Resources()
    parser.feed(html)
    for tag, value in parser.items:
        parts = urlsplit(value)
        if parts.scheme in {'http', 'https'} or value.startswith('//'):
            errors.append(f'加载了外部资源，离线无法打开：<{tag}> {value}')
        elif parts.scheme in {'', 'file'} and parts.path and not (path.parent / unquote(parts.path)).exists():
            errors.append(f'本地资源缺失：{value}')
    if re.search(r'@import\b|url\(\s*["\']?(?:https?:)?//', html):
        errors.append('样式中引用了外部资源')

    # 2. 数据块与引擎。
    raw = script_block(html, 'preview-data')
    engine = script_block(html, 'preview-engine')
    flow = script_block(html, 'preview-flow')
    if raw is None or engine is None or flow is None:
        return errors + ['缺少 preview-data / preview-engine / preview-flow 脚本块，未按模板生成'], notes
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return errors + [f'preview-data 不是合法 JSON：{exc}'], notes
    if not isinstance(data, dict):
        return errors + ['preview-data 顶层必须是对象'], notes
    template_engine = script_block(TEMPLATE.read_text(encoding='utf-8'), 'preview-engine')
    if path.resolve() != TEMPLATE.resolve() and normalize(engine) != normalize(template_engine or ''):
        errors.append('引擎与 templates/interactive-preview.html 不一致；功能差异只写在 preview-data 与 preview-flow')

    ui_raw = script_block(html, 'preview-ui')
    if ui_raw is not None:
        try:
            ui = json.loads(ui_raw)
            design, layers = ui.get('design'), ui.get('layers')
            if not (isinstance(design, list) and len(design) == 2 and isinstance(layers, dict) and layers):
                errors.append('preview-ui 缺少 design 或 layers；用 scripts/build_preview_ui.py 重新生成')
            else:
                for name, layer in layers.items():
                    if not str(layer.get('src', '')).startswith('data:image/'):
                        errors.append(f'界面图层 {name} 没有内嵌图片')
                    if not layer.get('prefab'):
                        errors.append(f'界面图层 {name} 没有记录来源 prefab')
        except (ValueError, AttributeError) as exc:
            errors.append(f'preview-ui 不是合法 JSON：{exc}')

    # 3. 主案对应关系。
    meta = data.get('meta') if isinstance(data.get('meta'), dict) else {}
    if not meta.get('feature'):
        errors.append('meta.feature 为空')
    headings: set[str] = set()
    source = path.parent / str(meta.get('source') or '')
    if not meta.get('source') or not source.is_file():
        errors.append(f'meta.source 指向的主案不存在：{meta.get("source")}')
    else:
        headings, latest = headings_and_version(source)
        if latest and meta.get('source_version') != latest:
            errors.append(f'预演依据 {meta.get("source_version")}，主案已是 {latest}；按变更重审受影响场景后再更新版本')
        elif not latest:
            notes.append('主案变更记录中未识别到版本号，未核对版本')

    # 4. 规则、前置条件、场景、待定细节。
    rules = data.get('rules') if isinstance(data.get('rules'), list) else []
    if not rules:
        errors.append('rules 为空：预演必须登记所演示的主案规则')
    rule_ids = set()
    for rule in rules:
        rid = rule.get('id') if isinstance(rule, dict) else None
        if not rid or not rule.get('summary') or not rule.get('section'):
            errors.append(f'规则缺少 id / section / summary：{rule}')
            continue
        if rid in rule_ids:
            errors.append(f'规则 id 重复：{rid}')
        rule_ids.add(rid)
        leaf = str(rule['section']).split('>')[-1].strip()
        if headings and leaf not in headings:
            errors.append(f'{rid} 引用的章节在主案中不存在：{rule["section"]}')

    for param in data.get('params') or []:
        if not isinstance(param, dict) or not param.get('id') or not param.get('label') or param.get('type') not in PARAM_TYPES:
            errors.append(f'前置条件缺少 id / label 或类型无效：{param}')
        elif param.get('origin') not in {'主案', '示意'}:
            errors.append(f'前置条件 {param["id"]} 须标明 origin：主案（规则给出的值）或 示意（演示用，非规则）')

    gaps = data.get('gaps') or []
    gap_ids = set()
    for gap in gaps:
        if not isinstance(gap, dict) or not gap.get('id') or not gap.get('question') or not gap.get('where'):
            errors.append(f'待定细节缺少 id / question / where：{gap}')
            continue
        gap_ids.add(gap['id'])
        if gap.get('status') == 'resolved':
            errors.append(f'{gap["id"]} 已拍板：结论回写主案并更新场景后，从预演中删除该条')
        elif allow_open_gaps:
            notes.append(f'待定细节 {gap["id"]}：{gap["question"]}')
        else:
            errors.append(f'待定细节未拍板 {gap["id"]}：{gap["question"]}（评审中可加 --allow-open-gaps）')

    scenarios = data.get('scenarios') if isinstance(data.get('scenarios'), list) else []
    if not scenarios:
        errors.append('scenarios 为空：至少覆盖主流程')
    covered, scenario_ids = set(), set()
    for sc in scenarios:
        sid = sc.get('id') if isinstance(sc, dict) else None
        expect = sc.get('expect') if isinstance(sc, dict) else None
        if not sid or not sc.get('name') or not sc.get('steps') or not isinstance(expect, dict):
            errors.append(f'场景缺少 id / name / steps / expect：{sid or sc}')
            continue
        if sid in scenario_ids:
            errors.append(f'场景 id 重复：{sid}')
        scenario_ids.add(sid)
        if not expect.get('result') or 'screen' not in expect:
            errors.append(f'{sid} 的 expect 须写明 screen 与 result')
        hits = expect.get('hits') or []
        if not hits and not expect.get('gaps'):
            errors.append(f'{sid} 没有预期命中的规则或待定细节')
        for rid in hits:
            if rid not in rule_ids:
                errors.append(f'{sid} 引用了未登记的规则：{rid}')
        for gid in expect.get('gaps') or []:
            if gid not in gap_ids:
                errors.append(f'{sid} 引用了未登记的待定细节：{gid}')
        covered.update(hits)
    for rid in sorted(rule_ids - covered):
        errors.append(f'规则 {rid} 没有任何场景覆盖')

    # 5. 回放。
    if static:
        notes.append('场景回放未执行（--static）；静态检查通过不等于流程可走通')
        return errors, notes
    node = shutil.which('node')
    if not node:
        errors.append('未找到 node，无法回放场景；安装 Node 后重试，或加 --static 明确只做静态检查')
        return errors, notes
    proc = subprocess.run([node, str(RUNNER), str(path)], capture_output=True, text=True, encoding='utf-8')
    try:
        result = json.loads(proc.stdout)
    except ValueError:
        return errors + [f'场景回放失败：{(proc.stderr or proc.stdout).strip()[:300]}'], notes
    if result.get('fatal'):
        return errors + [f'预演脚本无法运行：{result["fatal"]}'], notes
    errors.extend(result.get('renderErrors', []))
    for sc in scenarios:
        if not isinstance(sc, dict) or sc.get('id') not in scenario_ids:
            continue
        sid, expect, got = sc['id'], sc['expect'], result['scenarios'].get(sc['id'], {})
        if got.get('error'):
            errors.append(f'{sid} 回放出错：{got["error"]}')
            continue
        if got.get('screen') != expect.get('screen') or got.get('modal') != expect.get('modal'):
            errors.append(f'{sid} 结束位置不符：预期 {expect.get("screen")}/{expect.get("modal")}，'
                          f'实际 {got.get("screen")}/{got.get("modal")}')
        for key, label in (('hits', '规则'), ('gaps', '待定细节')):
            want, real = sorted(set(expect.get(key) or [])), sorted(set(got.get(key) or []))
            if want != real:
                errors.append(f'{sid} 命中{label}不符：预期 {want}，实际 {real}')
    return errors, notes


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('preview', type=Path)
    parser.add_argument('--allow-open-gaps', action='store_true')
    parser.add_argument('--static', action='store_true')
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    errors, notes = check_preview(args.preview, allow_open_gaps=args.allow_open_gaps, static=args.static)
    for note in notes:
        print(f'提示：{note}')
    for error in errors:
        print(f'问题：{error}')
    if errors:
        return 1
    print('交互预演机械检查通过；仍须在浏览器中逐场景走查。')
    if args.open:
        opened = webbrowser.open(args.preview.resolve().as_uri())
        print('已用默认浏览器打开。' if opened else f'未能调起浏览器，请手动打开：{args.preview.resolve()}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
