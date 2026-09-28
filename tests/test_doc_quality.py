import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def quality(tmp_path, text):
    doc = tmp_path / 'doc.md'
    doc.write_text(text, encoding='utf-8')
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/check_doc_quality.py'), str(doc), '--json'], capture_output=True, text=True, encoding='utf-8')
    return proc, json.loads(proc.stdout) if proc.stdout else []


def test_bad_document_reports_locations_without_changing_input(tmp_path):
    text = '# Rules\n\n- one；two\n\n{{placeholder}}\n\n[missing](missing.md)\n'
    proc, issues = quality(tmp_path, text)
    assert proc.returncode == 1, proc.stderr
    assert {i['code'] for i in issues} >= {'semicolon', 'placeholder', 'missing-link'}
    assert all(i['line'] > 0 for i in issues)
    assert (tmp_path / 'doc.md').read_text(encoding='utf-8') == text


def test_code_examples_and_legitimate_red_markup_are_not_errors(tmp_path):
    proc, issues = quality(tmp_path, '# Rules\n\n{{red:Text}}\n\n```md\n- a；b\n{{example}}\n[missing](x.md)\n```\n')
    assert proc.returncode == 0, proc.stderr
    assert issues == []


def test_html_and_encoded_paths_are_checked(tmp_path):
    (tmp_path / 'existing image.png').write_bytes(b'image')
    proc, issues = quality(tmp_path, '# Rules\n\n![ok](existing%20image.png)\n\n<table><tr><td><img src="absent.png"></td></tr></table>\n')
    assert proc.returncode == 1, proc.stderr
    assert [i['code'] for i in issues] == ['missing-link']


def test_reference_links_are_checked(tmp_path):
    proc, issues = quality(tmp_path, '# Rules\n\n[details][rules]\n\n[rules]: missing.md\n')
    assert proc.returncode == 1, proc.stderr
    assert 'missing-link' in {i['code'] for i in issues}


def test_frozen_fixture_meets_current_format():
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/check_doc_quality.py'), str(ROOT / 'tests/fixtures/small-requirement.md')], capture_output=True)
    assert proc.returncode == 0


def test_inline_code_is_not_checked_as_prose(tmp_path):
    proc, issues = quality(tmp_path, '# Rules\n\n- 字段 `a；b` 与 `TODO` 原样保留，示例 `[x](missing.md)`\n')
    assert proc.returncode == 0, issues
    assert issues == []


def test_baseline_reports_only_newly_introduced_issues(tmp_path):
    git = lambda *a: subprocess.run(['git', '-C', str(tmp_path), *a], check=True, capture_output=True)
    git('init', '-q')
    doc = tmp_path / 'doc.md'
    doc.write_text('# Rules\n\n- 旧规则；已有\n', encoding='utf-8')
    git('add', 'doc.md')
    git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base')
    doc.write_text('# Rules\n\n- 新增在前；问题\n\n- 旧规则；已有\n', encoding='utf-8')
    cmd = [sys.executable, str(ROOT / 'scripts/check_doc_quality.py'), str(doc), '--json']
    full = json.loads(subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8').stdout)
    proc = subprocess.run(cmd + ['--baseline', 'HEAD'], capture_output=True, text=True, encoding='utf-8')
    fresh = json.loads(proc.stdout)
    assert len(full) == 2
    assert proc.returncode == 1
    assert [i['line'] for i in fresh] == [3]
