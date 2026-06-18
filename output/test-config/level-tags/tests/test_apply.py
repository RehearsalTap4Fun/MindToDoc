import importlib
import math
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook


HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))


def _make_minimal_xlsx(tmp_path: Path, *, tag_overrides: dict[int, str] | None = None,
                       break_id: bool = False, missing_tag_def: bool = False,
                       extra_tag_def: bool = False) -> Path:
    """构造一个最小可用的 LevelTagCfg.xlsx。"""
    import level_tag_lib  # noqa
    importlib.reload(level_tag_lib)
    import generate_level_tag_template as g
    importlib.reload(g)
    out = tmp_path / "LevelTagCfg.xlsx"
    g.generate(out)

    from openpyxl import load_workbook
    wb = load_workbook(out)
    ws = wb["LevelTags"]
    if tag_overrides:
        for level_id, tags_str in tag_overrides.items():
            row_idx = 9 + (level_id - 1)
            ws.cell(row_idx, 5, tags_str)
    if break_id:
        ws.cell(9, 1, 999)

    td = wb["TagDef"]
    if missing_tag_def:
        td.delete_rows(9 + len(level_tag_lib.TAG_REGISTRY) - 1, 1)
    if extra_tag_def:
        td.cell(9 + len(level_tag_lib.TAG_REGISTRY), 1, "ghost_tag_xyz")
    wb.save(out)
    return out


def _registry_tags():
    import level_tag_lib as lib
    return list(lib.TAG_REGISTRY.keys())


def test_load_missing_file_raises(tmp_path):
    import apply_level_tags as app
    importlib.reload(app)
    with pytest.raises(FileNotFoundError):
        app.load_level_tag_cfg(tmp_path / "absent.xlsx")


def test_load_clean_file_returns_500_rows(tmp_path):
    out = _make_minimal_xlsx(tmp_path)
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    assert len(rows) == 500
    assert rows[0]["ID"] == 1
    assert rows[-1]["ID"] == 500
    assert rows[0]["Tags"] == []


def test_load_with_tags_parses_them(tmp_path):
    out = _make_minimal_xlsx(tmp_path, tag_overrides={
        100: "boss",
        200: "hard_plus, set_piece",
        300: "must_win,no_modifier",
    })
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    assert rows[99]["Tags"] == ["boss"]
    assert rows[199]["Tags"] == ["hard_plus", "set_piece"]
    assert rows[299]["Tags"] == ["must_win", "no_modifier"]


def test_validate_id_break(tmp_path):
    out = _make_minimal_xlsx(tmp_path, break_id=True)
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    with pytest.raises(app.ValidationError) as ei:
        app.validate_loaded(rows, td_tags=set(_registry_tags()))
    assert any("ID" in e for e in ei.value.errors)


def test_validate_unknown_tag(tmp_path):
    out = _make_minimal_xlsx(tmp_path, tag_overrides={42: "ghost_tag_xyz"})
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    with pytest.raises(app.ValidationError) as ei:
        app.validate_loaded(rows, td_tags=set(_registry_tags()))
    assert any("ghost_tag_xyz" in e for e in ei.value.errors)


def test_validate_mutex_violation(tmp_path):
    out = _make_minimal_xlsx(tmp_path, tag_overrides={50: "hard_plus,easy_minus"})
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    with pytest.raises(app.ValidationError) as ei:
        app.validate_loaded(rows, td_tags=set(_registry_tags()))
    assert any("mutex" in e.lower() or "互斥" in e for e in ei.value.errors)


def test_validate_tag_def_drift(tmp_path):
    out = _make_minimal_xlsx(tmp_path, missing_tag_def=True)
    import apply_level_tags as app
    importlib.reload(app)
    td_tags = app.load_tag_def(out)
    import level_tag_lib as lib
    assert td_tags != set(lib.TAG_REGISTRY.keys())
