import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'vendor/skills/slg-testcase-generator/scripts/validate_cases.py'
spec = importlib.util.spec_from_file_location('case_validation', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def validate(tmp_path, rows):
    p = tmp_path / 'cases.json'; p.write_text(json.dumps(rows), encoding='utf-8')
    v = module.CaseValidator(strict=True)
    valid = v.validate_file(str(p))
    return valid, v.errors


@pytest.mark.parametrize('rows', [
    [['TC1', 'm', 'check', 'act', '', '']],
    [['TC1', 'm', 'check', 'act', 'ok', ''], ['TC1', '', '', '', 'ok', '']],
    [['TC1', 'm', 'check', '', 'ok', '']],
    [['TC1', 'm', 'check', 'act', 'ok', ''], ['TC2', 'new module', 'new', '', 'ok', '']],
    [],
])
def test_unexecutable_cases_fail(tmp_path, rows):
    valid, errors = validate(tmp_path, rows)
    assert not valid
    assert errors


@pytest.mark.parametrize('remark', ['', '配置表ActivityCfg-Rate', '另一项与配置一致'])
def test_source_note_cannot_hide_literal_probability(tmp_path, remark):
    valid, errors = validate(tmp_path, [['TC1', 'm', 'check', 'act', '概率为50%', remark]])
    assert not valid
    assert any('硬编码' in e for e in errors)


def test_valid_step_inheritance_and_config_reference_pass(tmp_path):
    valid, errors = validate(tmp_path, [['TC1', 'm', 'check', 'act', '概率与配置一致', '配置表ActivityCfg-Rate'], ['TC2', '', '', '', '显示成功', '']])
    assert valid, errors
