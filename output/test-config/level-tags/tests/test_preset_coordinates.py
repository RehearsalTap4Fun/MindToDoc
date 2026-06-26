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


def _pos_tuple(text):
    value = _pos(text)
    return float(value["x"]), float(value.get("y", 0)), float(value["z"])


def _player_pos_tuple(player):
    pos = player["pos"]
    return float(pos["x"]), float(pos.get("y", 0)), float(pos["z"])


def _distance_xz(a, b):
    return math.hypot(float(a[0]) - float(b[0]), float(a[2]) - float(b[2]))


def _line_distance_xz(point, start, end):
    px, pz = float(point[0]), float(point[2])
    sx, sz = float(start[0]), float(start[2])
    ex, ez = float(end[0]), float(end[2])
    vx, vz = ex - sx, ez - sz
    wx, wz = px - sx, pz - sz
    denom = vx * vx + vz * vz
    if denom <= 1e-9:
        return math.hypot(px - sx, pz - sz), 0.0
    t = (wx * vx + wz * vz) / denom
    cx, cz = sx + t * vx, sz + t * vz
    return math.hypot(px - cx, pz - cz), t


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
        assert math.isclose(float(ball["x"]), round(expected_x, 1), abs_tol=1e-6), (row, owner)
        assert math.isclose(float(ball["z"]), round(expected_z, 1), abs_tol=1e-6), (row, owner)


def test_slice_preset_fields_are_complete_and_parseable():
    g, rows = _slice_preset_rows()
    valid_slice_types = set(g.SLICE_TYPE_NAME.values())
    valid_duties = set(g.PLAYER_AI_DUTY_ENUM.values())
    valid_modes = {"draw_line", "slingshot"}
    ids = [row["ID"] for row in rows]
    assert len(ids) == len(set(ids))

    for row in rows:
        assert row["SliceType"] in valid_slice_types, row
        assert isinstance(row["NameLcKey"], str) and row["NameLcKey"].startswith((
            "ActvSoccer_preset_name_",
            "ActvSoccer_preset_ref_",
        )), row
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
    assert len(rows) == 79
    assert Counter(row["SliceType"] for row in rows) == {
        "attack": 33,
        "free_kick": 14,
        "penalty": 6,
        "corner": 12,
        "throw_in": 9,
        "goalkeep": 5,
    }


def test_every_slice_preset_is_referenced_by_an_instance():
    _, presets = _slice_preset_rows()
    _, instances = _sheet_rows("ActvSoccerSliceInstanceCfg")
    preset_ids = {row["ID"] for row in presets}
    used_preset_ids = {row["PresetID"] for row in instances}

    assert preset_ids <= used_preset_ids


def test_instance_library_has_three_perceivable_variants_per_tier_type():
    g, rows = _sheet_rows("ActvSoccerSliceInstanceCfg")
    legacy_ids = {101, 102, 103, 201, 202, 203}
    regular_rows = [row for row in rows if row["ID"] not in legacy_ids and row["ID"] < 90000]
    # 实例 ID 编码: 1{stype:1}{seq:02d}, seq=(tier-1)*variant_count + variant (1-based)
    by_tier_type = {}
    for row in regular_rows:
        iid = row["ID"]
        stype = (iid // 100) - 10
        seq = iid % 100
        variant_count = g.SLICE_TYPE_VARIANT_COUNT[stype]
        tier = (seq - 1) // variant_count + 1
        variant = (seq - 1) % variant_count + 1
        by_tier_type.setdefault((tier, stype), set()).add(variant)

    assert len(by_tier_type) == 60
    for (_, stype), variants in by_tier_type.items():
        expected = set(range(1, g.SLICE_TYPE_VARIANT_COUNT[stype] + 1))
        assert variants == expected


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


def test_free_kick_and_corner_spacing_geometry_is_playable():
    g, rows = _slice_preset_rows()
    for row in rows:
        ball = _pos_tuple(row["BallPos"])
        target = _pos_tuple(row["TargetPoint"]) if row.get("TargetPoint") else (0.0, 0.0, 0.0)
        players = json.loads(row["PlayersInit"])
        home = [player for player in players if player["team"] == "home"]
        away = [player for player in players if player["team"] == "away"]

        if row["SliceType"] == "free_kick":
            wall = [
                player for player in away
                if int(player["duty"]) == g.PLAYER_AI_DUTY_ENUM["Defender"]
            ]
            assert wall, row
            for player in wall:
                assert _distance_xz(_player_pos_tuple(player), ball) >= 5.0, (row, player)

            line_distances = [
                _line_distance_xz(_player_pos_tuple(player), ball, target)
                for player in wall
            ]
            blocking_distances = [
                distance for distance, t in line_distances
                if 0.05 < t < 0.95
            ]
            assert blocking_distances, row
            assert min(blocking_distances) <= 0.8, row

        if row["SliceType"] == "corner":
            for i, first in enumerate(home):
                for second in home[i + 1:]:
                    assert _distance_xz(_player_pos_tuple(first), _player_pos_tuple(second)) >= 2.0, (
                        row,
                        first,
                        second,
                    )

            owner = int(row["BallOwner"])
            receivers = [player for player in home if int(player["idx"]) != owner]
            if receivers and target:
                vector = _pos(row["BallVector"])
                goalward_target = float(target[2]) > float(ball[2]) + 1.0 or float(vector["z"]) > 0.3
                if not goalward_target:
                    continue
                nearest = min(receivers, key=lambda player: _distance_xz(_player_pos_tuple(player), target))
                assert float(nearest["pos"]["z"]) >= float(ball[2]) - 1.0, (row, nearest)


def test_tap_in_rebound_and_throw_in_targets_have_receivers():
    _, rows = _slice_preset_rows()
    for row in rows:
        target = _pos_tuple(row["TargetPoint"]) if row.get("TargetPoint") else None
        if not target:
            continue
        tags = set(json.loads(row.get("Tags") or "[]"))
        players = json.loads(row["PlayersInit"])
        owner = int(row["BallOwner"])
        receivers = [
            player for player in players
            if player["team"] == "home" and int(player["idx"]) != owner
        ]
        if row["SliceType"] == "attack" and tags & {"tap_in", "rebound"}:
            assert receivers, row
            nearest = min(receivers, key=lambda player: _distance_xz(_player_pos_tuple(player), target))
            assert _distance_xz(_player_pos_tuple(nearest), target) <= 5.0, (row, nearest)
        if row["SliceType"] == "throw_in":
            assert receivers, row
            nearest = min(receivers, key=lambda player: _distance_xz(_player_pos_tuple(player), target))
            assert _distance_xz(_player_pos_tuple(nearest), target) <= 3.0, (row, nearest)


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
