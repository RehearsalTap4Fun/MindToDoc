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


def test_set_piece_inserts_freekick_and_penalty():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["set_piece"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    assert any(s // 10 % 10 == 2 for s in sl), f"无 free_kick: {sl}"
    assert any(s // 10 % 10 == 3 for s in sl), f"无 penalty: {sl}"


def test_corner_focus_makes_last_corner_v2():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["corner_focus"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    last = sl[-1]
    assert last // 10 % 10 == 4 and last % 10 == 2, f"末位非 corner v2: {last}"


def test_gk_test_makes_last_goalkeep_v2():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["gk_test"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    last = sl[-1]
    assert last // 10 % 10 == 6 and last % 10 == 2, f"末位非 goalkeep v2: {last}"


def test_long_match_adds_one_slice_capped_at_5():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx(slice_count=4)
    lib.TAG_REGISTRY["long_match"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    assert len(sl) == 5

    ctx2 = _make_ctx(slice_count=5)
    ctx2.level_row["SliceList"] = "[541,551,561,511,521]"
    lib.TAG_REGISTRY["long_match"].patch(ctx2)
    assert len(json.loads(ctx2.level_row["SliceList"])) == 5  # 上限 5


def test_short_match_removes_one_floor_at_2():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["short_match"].patch(ctx)
    assert len(json.loads(ctx.level_row["SliceList"])) == 3

    ctx2 = _make_ctx()
    ctx2.level_row["SliceList"] = "[541,551]"
    lib.TAG_REGISTRY["short_match"].patch(ctx2)
    assert len(json.loads(ctx2.level_row["SliceList"])) == 2


def test_all_v2_flips_last_digit():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["all_v2"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    assert all(s % 10 == 2 for s in sl), f"非全 v2: {sl}"
