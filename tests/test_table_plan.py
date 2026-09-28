import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/dingtalk_table_inserter.py'
spec = importlib.util.spec_from_file_location('table_inserter', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize('entries,tables', [
    ([(3, 0, 'a', 'paragraph', '〚TBL-3〛')], ['table']),
    ([], ['table']),
    ([(0, 0, 'a', 'paragraph', '〚TBL-0〛'), (0, 2, 'b', 'paragraph', '〚TBL-0〛')], ['table']),
    ([(0, None, 'a', 'paragraph', '〚TBL-0〛')], ['table']),
    ([(0, 0, '', 'paragraph', '〚TBL-0〛')], ['table']),
    ([(0, 0, 'a', 'blockquote', 'text 〚TBL-0〛')], ['table']),
])
def test_invalid_snapshot_cannot_produce_destructive_plan(entries, tables):
    with pytest.raises(ValueError):
        module.build_plan(entries, tables, '〚TBL-', 'node')


def test_reverse_serial_plan_preserves_table_section_association():
    docs = [('a', '〚TBL-0〛'), ('text1', 'between'), ('b', '〚TBL-1〛 〚TBL-2〛'), ('text2', 'tail')]
    entries = [(0, 0, 'a', 'paragraph', docs[0][1]), (1, 2, 'b', 'paragraph', docs[2][1]), (2, 2, 'b', 'paragraph', docs[2][1])]
    plan = module.build_plan(entries, ['zero', 'one', 'two'], '〚TBL-', 'node')
    for op in plan:
        if op['op'] == 'append_table':
            docs.insert(op['insert_index'], ('table', op['markdown']))
        elif op['op'] == 'delete_block':
            docs = [d for d in docs if d[0] != op['blk_id']]
    assert [d[1] for d in docs] == ['zero', 'between', 'one', 'two', 'tail']


def test_cli_mismatch_returns_error_and_does_not_write_plan(tmp_path):
    blocks = tmp_path / 'blocks.json'; blocks.write_text('[]', encoding='utf-8')
    tables = tmp_path / 'tables.json'; tables.write_text('["table"]', encoding='utf-8')
    out = tmp_path / 'plan.json'
    proc = subprocess.run([sys.executable, str(SCRIPT), '--blocks', str(blocks), '--tables', str(tables), '--node-id', 'test', '--out', str(out)], capture_output=True)
    assert proc.returncode != 0
    assert not out.exists()


def test_empty_document_needs_no_operations():
    assert module.build_plan([], [], '〚TBL-', 'node') == []
