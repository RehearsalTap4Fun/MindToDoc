import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(manifest):
    return subprocess.run([sys.executable, str(ROOT / 'scripts/check_delivery.py'), str(manifest)], capture_output=True, text=True, encoding='utf-8')


def test_review_record_is_invalidated_by_source_or_artifact_changes(tmp_path):
    source = tmp_path / 'main.md'; source.write_text('main v1', encoding='utf-8')
    asset = tmp_path / 'ui.md'; asset.write_text('ui v1', encoding='utf-8')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    data = {'schema_version': 1, 'feature': 'test', 'mode': 'small', 'source': {'path': 'main.md', 'sha256': digest(source)}, 'artifacts': [{'kind': 'ui', 'path': 'ui.md', 'sha256': digest(asset), 'status': 'reviewed', 'review_note': '规则与主案逐项核对'}]}
    manifest = tmp_path / 'delivery.json'; manifest.write_text(json.dumps(data), encoding='utf-8')
    assert run(manifest).returncode == 0
    source.write_text('main v2', encoding='utf-8')
    assert run(manifest).returncode == 1
    source.write_text('main v1', encoding='utf-8'); asset.write_text('ui v2', encoding='utf-8')
    assert run(manifest).returncode == 1


def test_complete_mode_cannot_omit_fixed_artifacts(tmp_path):
    source = tmp_path / 'main.md'; source.write_text('main', encoding='utf-8')
    data = {'schema_version': 1, 'feature': 'test', 'mode': 'complete', 'source': {'path': 'main.md', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}, 'artifacts': []}
    manifest = tmp_path / 'delivery.json'; manifest.write_text(json.dumps(data), encoding='utf-8')
    assert run(manifest).returncode == 1


def test_pending_review_is_not_reported_complete(tmp_path):
    main = tmp_path / 'main.md'; main.write_text('main', encoding='utf-8')
    h = hashlib.sha256(main.read_bytes()).hexdigest()
    manifest = tmp_path / 'delivery.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'feature': 'test', 'mode': 'small', 'source': {'path': 'main.md', 'sha256': h}, 'artifacts': [{'kind': 'ui', 'path': 'main.md', 'sha256': h, 'status': 'pending', 'review_note': ''}]}), encoding='utf-8')
    assert run(manifest).returncode == 1
