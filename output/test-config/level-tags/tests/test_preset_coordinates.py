import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "test-config"))


def _slice_preset_rows():
    import generate_activity_soccer_test_config as g

    wb = g.build_workbook(g.LcRegistry())
    ws = wb["ActvSoccerSlicePresetCfg"]
    fields = [ws.cell(3, col).value for col in range(1, ws.max_column + 1)]
    rows = []
    for row_idx in range(9, ws.max_row + 1):
        row = {
            field: ws.cell(row_idx, col_idx).value
            for col_idx, field in enumerate(fields, start=1)
            if field
        }
        if row.get("ID") is None:
            continue
        rows.append(row)
    return g, rows


def _sheet_rows(sheet_name):
    import generate_activity_soccer_test_config as g

    wb = g.build_workbook(g.LcRegistry())
    ws = wb[sheet_name]
    fields = [ws.cell(3, col).value for col in range(1, ws.max_column + 1)]
    rows = []
    for row_idx in range(9, ws.max_row + 1):
        row = {
            field: ws.cell(row_idx, col_idx).value
            for col_idx, field in enumerate(fields, start=1)
            if field
        }
        if row.get("ID") is None:
            continue
        rows.append(row)
    return g, rows


def _pos(text):
    return json.loads(text)


def test_slice_preset_coordinates_are_inside_protocol_bounds():
    g, rows = _slice_preset_rows()
    for row in rows:
        ball = _pos(row["BallPos"])
        assert -g.FIELD_X_HALF <= float(ball["x"]) <= g.FIELD_X_HALF, row
        assert 0 <= float(ball["y"]) <= g.GOAL_HEIGHT, row
        assert g.FIELD_Z_FAR <= float(ball["z"]) <= g.FIELD_Z_NEAR, row

        target = row.get("TargetPoint")
        if not target:
            continue
        pos = _pos(target)
        assert -g.FIELD_X_HALF <= float(pos["x"]) <= g.FIELD_X_HALF, row
        assert 0 <= float(pos["y"]) <= g.GOAL_HEIGHT, row
        assert g.FIELD_Z_FAR <= float(pos["z"]) <= g.FIELD_Z_NEAR, row

        for player in json.loads(row["PlayersInit"]):
            player_pos = player["pos"]
            assert -g.FIELD_X_HALF <= float(player_pos["x"]) <= g.FIELD_X_HALF, (row, player)
            assert 0 <= float(player_pos["y"]) <= g.GOAL_HEIGHT, (row, player)
            assert g.FIELD_Z_FAR <= float(player_pos["z"]) <= g.FIELD_Z_NEAR, (row, player)


def test_non_goalkeep_ball_is_offset_in_owner_facing_direction():
    g, rows = _slice_preset_rows()
    for row in rows:
        if row["SliceType"] == "goalkeep":
            continue
        ball = _pos(row["BallPos"])
        players = json.loads(row["PlayersInit"])
        owner_idx = int(row["BallOwner"])
        owner = next(
            player for player in players
            if player["team"] == "home" and int(player["idx"]) == owner_idx
        )
        yaw = math.radians(float(owner["facing"]))
        expected_x = float(owner["pos"]["x"]) + math.sin(yaw) * g.BALL_CONTROL_DISTANCE
        expected_z = float(owner["pos"]["z"]) + math.cos(yaw) * g.BALL_CONTROL_DISTANCE
        assert math.isclose(float(ball["x"]), expected_x, abs_tol=1e-3), (row, owner)
        assert math.isclose(float(ball["z"]), expected_z, abs_tol=1e-3), (row, owner)


def test_slice_preset_fields_are_complete_and_parseable():
    g, rows = _slice_preset_rows()
    valid_slice_types = set(g.SLICE_TYPE_NAME.values())
    valid_duties = set(g.PLAYER_AI_DUTY_ENUM.values())
    valid_modes = {"draw_line", "slingshot"}
    ids = [row["ID"] for row in rows]
    assert len(ids) == len(set(ids))

    for row in rows:
        assert row["SliceType"] in valid_slice_types, row
        assert isinstance(row["NameLcKey"], str) and row["NameLcKey"].startswith("ActvSoccer_preset_name_"), row
        assert isinstance(json.loads(row["Tags"]), list), row

        vector = _pos(row["BallVector"])
        vector_values = [float(vector[key]) for key in ("x", "y", "z")]
        assert any(abs(value) > 1e-6 for value in vector_values), row
        assert all(-1.0 <= value <= 1.0 for value in vector_values), row

        players = json.loads(row["PlayersInit"])
        owner = int(row["BallOwner"])
        assert any(player["team"] == "home" and int(player["idx"]) == owner for player in players), row
        seen = set()
        for player in players:
            assert player["team"] in {"home", "away"}, (row, player)
            assert int(player["duty"]) in valid_duties, (row, player)
            key = (player["team"], int(player["idx"]))
            assert key not in seen, (row, player)
            seen.add(key)
            assert -180.0 <= float(player["facing"]) <= 180.0, (row, player)

        assert 30.0 <= float(row["CameraFov"]) <= 70.0, row
        assert 0.0 <= float(row["OperableAngle"]) <= 180.0, row
        assert 0.0 <= float(row["AngleSpanMin"]) <= float(row["AngleSpanMax"]) <= 180.0, row
        assert 0.0 <= float(row["AngleMaxCenterShift"]) <= 180.0, row
        assert 0.0 <= float(row["AngleMargin"]) <= 90.0, row
        assert isinstance(json.loads(row["TypePayload"]), dict), row
        assert set(json.loads(row["RecommendedModes"])).issubset(valid_modes), row
        assert isinstance(row["Remark"], str) and len(row["Remark"]) >= 20, row


def test_slice_preset_library_has_production_distribution():
    _, rows = _slice_preset_rows()
    assert len(rows) == 50
    assert Counter(row["SliceType"] for row in rows) == {
        "attack": 14,
        "free_kick": 9,
        "penalty": 5,
        "corner": 10,
        "throw_in": 8,
        "goalkeep": 4,
    }


def test_every_slice_preset_is_referenced_by_an_instance():
    _, presets = _slice_preset_rows()
    _, instances = _sheet_rows("ActvSoccerSliceInstanceCfg")
    preset_ids = {row["ID"] for row in presets}
    used_preset_ids = {row["PresetID"] for row in instances}

    assert preset_ids <= used_preset_ids


def test_instance_library_has_three_perceivable_variants_per_tier_type():
    _, rows = _sheet_rows("ActvSoccerSliceInstanceCfg")
    legacy_ids = {101, 102, 103, 201, 202, 203}
    regular_rows = [row for row in rows if row["ID"] not in legacy_ids and row["ID"] < 90000]
    by_tier_type = {}
    for row in regular_rows:
        tier = row["ID"] // 100
        stype = (row["ID"] // 10) % 10
        variant = row["ID"] % 10
        by_tier_type.setdefault((tier, stype), set()).add(variant)

    assert len(by_tier_type) == 60
    assert all(variants >= {1, 2, 3} for variants in by_tier_type.values())


def test_narrow_angle_skips_zero_angle_slice_types():
    _, inst_rows = _sheet_rows("ActvSoccerSliceInstanceCfg")
    offenders = []
    for inst in inst_rows:
        if inst["ModifierID"] != 4006:
            continue
        if inst["SliceType"] in {"penalty", "goalkeep"}:
            offenders.append(inst)
    assert offenders == []


def test_slice_instance_contains_merged_ai_fields_and_no_slice_ai_sheet():
    g, rows = _sheet_rows("ActvSoccerSliceInstanceCfg")
    required_fields = {
        "AiProfileID", "GoalkeeperAiID", "DefenderAiID", "ShooterAiID",
        "ModifierID", "IsGuideAi", "RewindRandom", "OverrideReactionTimeMs",
    }
    assert rows
    assert required_fields.issubset(rows[0].keys())

    wb = g.build_workbook(g.LcRegistry())
    assert "ActvSoccerSliceAiCfg" not in wb.sheetnames


def test_free_kick_wall_count_matches_players_init():
    _, rows = _slice_preset_rows()
    for row in rows:
        if row["SliceType"] != "free_kick":
            continue
        payload = json.loads(row["TypePayload"])
        players = json.loads(row["PlayersInit"])
        defenders = [
            player for player in players
            if player["team"] == "away" and int(player["duty"]) == 2
        ]
        assert payload["wall_count"] == len(defenders), row


def test_slice_type_specific_field_invariants_apply_to_all_matching_presets():
    g, rows = _slice_preset_rows()
    for row in rows:
        ball = _pos(row["BallPos"])
        if row["SliceType"] == "penalty":
            assert (float(ball["x"]), float(ball["z"])) == (g.PENALTY_SPOT[0], g.PENALTY_SPOT[2]), row
        if row["SliceType"] == "corner":
            assert (float(ball["x"]), float(ball["z"])) in {
                (g.CORNER_LEFT_BALL[0], g.CORNER_LEFT_BALL[2]),
                (g.CORNER_RIGHT_BALL[0], g.CORNER_RIGHT_BALL[2]),
            }, row
        if row["SliceType"] == "goalkeep":
            for player in json.loads(row["PlayersInit"]):
                if player["team"] == "home":
                    assert g.GOAL_AREA_Z_FAR <= float(player["pos"]["z"]) <= g.FIELD_Z_NEAR, (row, player)
