import importlib
import json

def _make_ctx(slice_count=4, tier=5, level_in_round=5):
    """构造一个最小可用的 PatchContext,默认 slice_count=4 便于阈值断言。"""
    import importlib, level_tag_lib as lib
    importlib.reload(lib)
    from level_tag_lib import PatchContext
    return PatchContext(
        level_row={
            "ID": 250, "IsTutorial": 0,
            "SliceList": "[541,551,561,511]",
            "AiProfileID": 1005, "WinThreshold": 3, "DrawThreshold": 2,
            "TicketCost": 1, "OpponentTeamID": 3025, "OpponentTeamStar": 3,
            "SeasonID": 25, "Remark": "",
        },
        slice_ai_rows=[],
        slice_instance_rows=[],
        new_id_alloc=lambda: 99999,
        level_in_round=level_in_round,
        tier=tier,
        library={"slice_count": slice_count},
    )


def test_registry_starts_empty_then_accepts_register():
    lib = importlib.import_module("level_tag_lib")
    importlib.reload(lib)
    assert "foo" not in lib.TAG_REGISTRY

    def noop_patch(ctx):
        pass

    spec = lib.TagSpec(
        name="foo",
        affects=("slice",),
        mutex_group=None,
        description="测试",
        patch=noop_patch,
    )
    lib.register(spec)
    assert "foo" in lib.TAG_REGISTRY
    assert lib.TAG_REGISTRY["foo"].mutex_group is None


def test_register_duplicate_raises():
    lib = importlib.import_module("level_tag_lib")
    importlib.reload(lib)

    def noop(ctx):
        pass

    spec = lib.TagSpec("dup", ("slice",), None, "x", noop)
    lib.register(spec)
    try:
        lib.register(spec)
    except ValueError as e:
        assert "dup" in str(e)
    else:
        raise AssertionError("expected ValueError on duplicate register")


def test_boss_sets_star5_and_full_win():
    import importlib, level_tag_lib as lib
    importlib.reload(lib)
    lib._register_level_only_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["boss"].patch(ctx)
    assert ctx.level_row["OpponentTeamStar"] == 5
    assert ctx.level_row["WinThreshold"] == 4   # = slice_count
    assert ctx.level_row["DrawThreshold"] == 3


def test_must_win_pushes_thresholds():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["must_win"].patch(ctx)
    assert ctx.level_row["WinThreshold"] == 4
    assert ctx.level_row["DrawThreshold"] == 3


def test_lenient_lowers_thresholds():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags()
    ctx = _make_ctx(slice_count=5)
    ctx.level_row["SliceList"] = "[541,551,561,511,521]"  # 5 个,与 slice_count 对齐
    lib.TAG_REGISTRY["lenient"].patch(ctx)
    assert ctx.level_row["WinThreshold"] == 2
    assert ctx.level_row["DrawThreshold"] == 1


def test_free_run_zeros_ticket():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["free_run"].patch(ctx)
    assert ctx.level_row["TicketCost"] == 0


def test_tutorial_marks_and_swaps_slices():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["tutorial"].patch(ctx)
    assert ctx.level_row["IsTutorial"] == 1
    assert ctx.level_row["TicketCost"] == 0
    assert ctx.level_row["SliceList"] == "[201,202,203]"
