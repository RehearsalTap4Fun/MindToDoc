import json
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def convert(tmp_path, text):
    source = tmp_path / 'source.md'
    source.write_text(text, encoding='utf-8')
    out = tmp_path / 'result.json'
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/md2jsonml.py'), str(source), str(out)], capture_output=True, text=True, encoding='utf-8')
    return proc, out


def test_paragraph_and_list_boundaries_survive_body_conversion(tmp_path):
    text = '# Rules\n\nFirst paragraph.\n\nSecond paragraph.\n\n- Item\n\nIndependent paragraph.\n'
    proc, out = convert(tmp_path, text)
    assert proc.returncode == 0, proc.stderr
    body = out.with_suffix('.body.md').read_text(encoding='utf-8')
    assert 'First paragraph.\n\nSecond paragraph.' in body
    assert '- Item\n\nIndependent paragraph.' in body


def test_soft_wrapped_paragraph_is_one_jsonml_block(tmp_path):
    proc, out = convert(tmp_path, '# Rules\n\nFirst line\ncontinues here.\n\nNext paragraph.\n')
    assert proc.returncode == 0, proc.stderr
    blocks = json.loads(out.read_text(encoding='utf-8'))[2:]
    assert [b[0] for b in blocks] == ['h1', 'p', 'p']
    assert 'continues here.' in json.dumps(blocks[1])


def test_markdown_image_and_legacy_annotation_share_ordered_markers(tmp_path):
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets/screen one.png').write_bytes(b'image')
    proc, out = convert(tmp_path, '# Rules\n\n![screen](<assets/screen one.png>)\n\n<!-- IMG: annotated | screen-id -->\n')
    assert proc.returncode == 0, proc.stderr
    images = json.loads(out.with_suffix('.images.json').read_text(encoding='utf-8'))
    assert [i['marker'] for i in images] == ['〚IMG-0〛', '〚IMG-1〛']
    assert images[0]['kind'] == 'image'
    assert Path(images[0]['path']) == tmp_path / 'assets/screen one.png'
    assert images[1]['id'] == 'screen-id'
    assert '![' not in out.with_suffix('.body.md').read_text(encoding='utf-8')


def test_missing_image_fails_before_writing_any_output(tmp_path):
    proc, out = convert(tmp_path, '![missing](missing.png)\n')
    assert proc.returncode != 0
    assert not out.exists()
    assert not out.with_suffix('.images.json').exists()


def test_table_and_fenced_code_keep_content(tmp_path):
    proc, out = convert(tmp_path, '# Rules\n\n| Type | Text |\n|---|---|\n| int[] | amount {0} |\n\n```text\n![not image](missing.png)\n\nsecond\n```\n')
    assert proc.returncode == 0, proc.stderr
    tables = json.loads(out.with_suffix('.tables.json').read_text(encoding='utf-8'))
    assert r'int\[\]' in tables[0]
    assert '`{0}`' in tables[0]
    assert json.loads(out.with_suffix('.images.json').read_text(encoding='utf-8')) == []
    assert '\n\nsecond' in json.loads(out.read_text(encoding='utf-8'))[-1][1]['code']


@pytest.mark.parametrize('first,second', [('* first', '* second'), ('+ first', '+ second'), ('1) first', '2) second'), ('1. first', '2. second')])
def test_alternate_list_markers_never_merge_with_prose_or_each_other(tmp_path, first, second):
    text = f'Intro\n{first}\n{second}\n\nEnd\n'
    proc, out = convert(tmp_path, text)
    assert proc.returncode == 0, proc.stderr
    blocks = json.loads(out.read_text(encoding='utf-8'))[2:]
    assert len(blocks) == 4
    assert 'first' in json.dumps(blocks[1]) and 'second' not in json.dumps(blocks[1])
    assert 'second' in json.dumps(blocks[2])
    assert text.strip() == out.with_suffix('.body.md').read_text(encoding='utf-8').strip()


def test_missing_image_error_names_line_and_flag(tmp_path):
    proc, out = convert(tmp_path, '# Rules\n\n![missing](missing.png)\n')
    assert proc.returncode == 2
    assert 'source.md:3' in proc.stderr and '--allow-missing-images' in proc.stderr
    assert 'Traceback' not in proc.stderr


def test_allow_missing_images_keeps_marker_and_flags_entry(tmp_path):
    source = tmp_path / 'source.md'
    source.write_text('# Rules\n\n![missing](missing.png)\n', encoding='utf-8')
    out = tmp_path / 'result.json'
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/md2jsonml.py'), str(source), str(out), '--allow-missing-images'], capture_output=True, text=True, encoding='utf-8')
    assert proc.returncode == 0, proc.stderr
    assert 'missing.png' in proc.stderr
    images = json.loads(out.with_suffix('.images.json').read_text(encoding='utf-8'))
    assert images[0]['missing'] is True and images[0]['marker'] == '〚IMG-0〛'


@pytest.mark.parametrize('text', [
    '<color=#0ea728><b>规则</b></color>\n1.第一条\n2.第二条\n',
    '<color=#0ea728><b>规则</b></color>\n1、第一条\n2）第二条\n',
    '首行  \n第一条\\\n第二条\n',
])
def test_preview_lines_without_markdown_spacing_stay_separate(tmp_path, text):
    proc, out = convert(tmp_path, text)
    assert proc.returncode == 0, proc.stderr
    blocks = json.loads(out.read_text(encoding='utf-8'))[2:]
    assert len(blocks) == 3
    assert '第一条' in json.dumps(blocks[1], ensure_ascii=False)
    assert '第二条' not in json.dumps(blocks[1], ensure_ascii=False)
    assert '\\\\' not in json.dumps(blocks, ensure_ascii=False)


def test_long_horizontal_rule_is_not_body_text(tmp_path):
    proc, out = convert(tmp_path, 'Above\n\n-----\n\nBelow\n')
    assert proc.returncode == 0, proc.stderr
    blocks = json.loads(out.read_text(encoding='utf-8'))[2:]
    assert '-----' not in json.dumps(blocks)
    assert len(blocks) == 2
