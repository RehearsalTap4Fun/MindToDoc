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


def record(manifest, *args):
    return subprocess.run([sys.executable, str(ROOT / 'scripts/check_delivery.py'), str(manifest), '--record', *map(str, args)], capture_output=True, text=True, encoding='utf-8')


def test_record_creates_manifest_and_updates_only_named_entry(tmp_path):
    (tmp_path / 'main.md').write_text('main', encoding='utf-8')
    (tmp_path / 'bi.md').write_text('bi', encoding='utf-8')
    (tmp_path / 'art.md').write_text('art', encoding='utf-8')
    manifest = tmp_path / 'deliveries/f.json'
    assert record(manifest, tmp_path / 'main.md', '--source', '--feature', 'f', '--mode', 'small').returncode == 0
    assert record(manifest, tmp_path / 'bi.md', '--kind', 'bi', '--status', 'reviewed').returncode == 2
    record(manifest, tmp_path / 'bi.md', '--kind', 'bi', '--status', 'reviewed', '--note', '字段与主案触发逐项核对')
    record(manifest, tmp_path / 'art.md', '--kind', 'art', '--status', 'reviewed', '--note', '资源清单核对')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    assert data['source']['path'] == '../main.md'
    assert [a['kind'] for a in data['artifacts']] == ['bi', 'art']
    assert run(manifest).returncode == 0
    (tmp_path / 'bi.md').write_text('bi v2', encoding='utf-8')
    art_hash = data['artifacts'][1]['sha256']
    assert run(manifest).returncode == 1
    record(manifest, tmp_path / 'bi.md', '--status', 'reviewed', '--note', '复核新增字段')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    assert data['artifacts'][1]['sha256'] == art_hash and len(data['artifacts']) == 2
    assert run(manifest).returncode == 0


def test_malformed_optional_fields_are_reported_per_item(tmp_path):
    main = tmp_path / 'main.md'; main.write_text('main', encoding='utf-8')
    h = hashlib.sha256(main.read_bytes()).hexdigest()
    manifest = tmp_path / 'delivery.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'feature': 'test', 'mode': 'small', 'known_issues': '待补图', 'source': {'path': 'main.md', 'sha256': h}, 'artifacts': [{'kind': 'ui', 'path': 'main.md', 'sha256': h, 'status': 'reviewed', 'review_note': None}]}), encoding='utf-8')
    proc = run(manifest)
    assert proc.returncode == 1
    assert '已登记待处理：待补图' in proc.stdout
    assert '尚未核验：main.md' in proc.stdout
    assert '无法核验' not in proc.stdout
