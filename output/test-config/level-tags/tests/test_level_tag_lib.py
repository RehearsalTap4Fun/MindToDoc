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


def test_set_piece_preserves_existing_slice_order_when_adding_missing_types():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    before = json.loads(ctx.level_row["SliceList"])
    lib.TAG_REGISTRY["set_piece"].patch(ctx)
    after = json.loads(ctx.level_row["SliceList"])
    retained = [s for s in after if s in before]
    assert retained == [s for s in before if s in retained]
    assert any(s // 10 % 10 == 2 for s in after), f"无 free_kick: {after}"
    assert any(s // 10 % 10 == 3 for s in after), f"无 penalty: {after}"
    assert len(after) <= 5


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


def _make_ctx_with_slice_ai():
    """构造带 SliceList 对应 SliceAi 行的 ctx,模拟 apply 层的现实输入。"""
    import importlib, level_tag_lib as lib
    importlib.reload(lib)
    lib._register_level_only_tags(); lib._register_slice_tags(); lib._register_ai_tags()
    counter = {"v": 90000}
    def alloc():
        counter["v"] += 1
        return counter["v"]
    sl_ids = [541, 551, 561, 511]
    return lib.PatchContext(
        level_row={
            "ID": 250, "IsTutorial": 0,
            "SliceList": json.dumps(sl_ids),
            "AiProfileID": 1005, "WinThreshold": 3, "DrawThreshold": 2,
            "TicketCost": 1, "OpponentTeamID": 3025, "OpponentTeamStar": 3,
            "SeasonID": 25, "Remark": "",
        },
        slice_ai_rows=[
            {"ID": 3100+i, "SliceID": sid, "AiProfileID": 1005,
             "GoalkeeperAiID": 2031, "DefenderAiID": 2032, "ShooterAiID": 0,
             "ModifierID": 4002, "IsGuideAi": 0, "RewindRandom": 1,
             "OverrideReactionTimeMs": 950, "Remark": ""}
            for i, sid in enumerate(sl_ids)
        ],
        slice_instance_rows=[
            {"ID": sid, "SliceType": "x", "PresetID": 1,
             "OverrideOperableAngle": 32.0, "ObjectiveType": "score",
             "ExtraObjectives": "[]", "Modifiers": "[]", "Remark": ""}
            for sid in sl_ids
        ],
        new_id_alloc=alloc, level_in_round=5, tier=5,
        library={"slice_count": 4},
    )


def test_hard_plus_bumps_profile_and_star():
    ctx = _make_ctx_with_slice_ai()
    import level_tag_lib as lib
    lib.TAG_REGISTRY["hard_plus"].patch(ctx)
    assert ctx.level_row["AiProfileID"] == 1006
    assert ctx.level_row["OpponentTeamStar"] == 4


def test_hard_plus_caps_at_1010_and_star5():
    ctx = _make_ctx_with_slice_ai()
    ctx.level_row["AiProfileID"] = 1010
    ctx.level_row["OpponentTeamStar"] = 5
    import level_tag_lib as lib
    lib.TAG_REGISTRY["hard_plus"].patch(ctx)
    assert ctx.level_row["AiProfileID"] == 1010
    assert ctx.level_row["OpponentTeamStar"] == 5


def test_easy_minus_floors_at_1001_and_star1():
    ctx = _make_ctx_with_slice_ai()
    ctx.level_row["AiProfileID"] = 1001
    ctx.level_row["OpponentTeamStar"] = 1
    import level_tag_lib as lib
    lib.TAG_REGISTRY["easy_minus"].patch(ctx)
    assert ctx.level_row["AiProfileID"] == 1001
    assert ctx.level_row["OpponentTeamStar"] == 1


def test_extreme_keeper_appends_virtual_slice_ai_and_instance():
    ctx = _make_ctx_with_slice_ai()
    instances_before = len(ctx.slice_instance_rows)
    slice_ais_before = len(ctx.slice_ai_rows)
    import level_tag_lib as lib
    lib.TAG_REGISTRY["extreme_keeper"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    assert all(s >= 90000 for s in sl), f"SliceList 仍含原 ID: {sl}"
    assert len(ctx.slice_instance_rows) == instances_before + len(sl)
    assert len(ctx.slice_ai_rows) == slice_ais_before + len(sl)
    new_ais = ctx.slice_ai_rows[slice_ais_before:]
    assert all(r["ModifierID"] == 4005 for r in new_ais)


def test_no_modifier_zeroes_modifier_in_virtual_rows():
    ctx = _make_ctx_with_slice_ai()
    import level_tag_lib as lib
    lib.TAG_REGISTRY["no_modifier"].patch(ctx)
    new_ais = [r for r in ctx.slice_ai_rows if r["ID"] >= 90000]
    assert len(new_ais) > 0
    assert all(r["ModifierID"] == 0 for r in new_ais)


def test_narrow_angle_sets_4006():
    ctx = _make_ctx_with_slice_ai()
    import level_tag_lib as lib
    lib.TAG_REGISTRY["narrow_angle"].patch(ctx)
    new_ais = [r for r in ctx.slice_ai_rows if r["ID"] >= 90000]
    assert all(r["ModifierID"] == 4006 for r in new_ais)
