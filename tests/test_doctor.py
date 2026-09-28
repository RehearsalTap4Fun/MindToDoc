import importlib.util
from pathlib import Path


def doctor():
    path = Path(__file__).parents[1] / 'scripts/doctor.py'
    spec = importlib.util.spec_from_file_location('doctor', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reports_missing_files_modules_and_external_skills(tmp_path):
    capability = {'files': ['missing.md'], 'modules': ['mindtodoc_nonexistent_module'], 'skills': ['missing-skill']}
    errors = doctor().check_capability(tmp_path, capability, [tmp_path])
    assert len(errors) == 3
    assert all('missing' in error or 'nonexistent' in error for error in errors)


def test_resolves_skill_root_without_importing_or_executing_skill(tmp_path):
    (tmp_path / 'external').mkdir()
    (tmp_path / 'external/SKILL.md').write_text('instructions', encoding='utf-8')
    assert doctor().check_capability(tmp_path, {'files': ['external/SKILL.md'], 'modules': ['json'], 'skills': ['external']}, [tmp_path]) == []
