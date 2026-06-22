import json
import sys
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
