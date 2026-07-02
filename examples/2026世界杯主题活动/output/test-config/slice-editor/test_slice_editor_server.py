import json
from pathlib import Path

import slice_editor_server as server


def test_build_editor_payload_contains_current_presets():
    payload = server.build_editor_payload()

    assert payload["coordinate_protocol"]["field_x_half"] == 18.0
    assert payload["coordinate_protocol"]["field_z_far"] == -60.0
    assert payload["default_angle"] == 120.0
    assert len(payload["presets"]) == 83
    first = payload["presets"][0]
    assert first["ID"] == 101
    assert first["SliceType"] == "attack"
    assert isinstance(first["PlayersInitParsed"], list)
    assert isinstance(first["BallPosParsed"], dict)
    assert "OperableAngle" not in first
    assert "AngleSpanMax" not in first


def test_save_edit_patch_writes_normalized_json(tmp_path):
    patch_path = tmp_path / "slice-preset-edits.json"
    payload = {
        "edits": [
            {
                "ID": 1001,
                "BallPos": {"x": 11.5, "y": 0, "z": -12.4},
                "BallVector": {"x": -0.1, "y": 0, "z": 0.99},
                "PlayersInit": [
                    {"team": "home", "idx": 0, "duty": 3, "pos": {"x": 12, "y": 0, "z": -13}, "facing": -6.0}
                ],
            }
        ]
    }

    result = server.save_edit_patch(payload, patch_path)

    assert result["saved"] == 1
    written = json.loads(patch_path.read_text(encoding="utf-8"))
    assert written["schema"] == "activity_soccer_slice_preset_edits.v1"
    assert written["edits"][0]["ID"] == 1001
    assert written["edits"][0]["BallPos"] == {"x": 11.5, "y": 0.0, "z": -12.4}
    assert "OperableAngle" not in written["edits"][0]


def test_save_edit_patch_rejects_unknown_fields(tmp_path):
    patch_path = tmp_path / "slice-preset-edits.json"
    payload = {"edits": [{"ID": 1001, "OperableAngle": 120}]}

    try:
        server.save_edit_patch(payload, patch_path)
    except ValueError as exc:
        assert "OperableAngle" in str(exc)
    else:
        raise AssertionError("unknown edit fields should be rejected")


def test_build_patch_from_xlsx_uses_latest_preset_shape():
    patch = server.build_patch_from_xlsx()

    assert patch["schema"] == "activity_soccer_slice_preset_edits.v1"
    assert len(patch["edits"]) == 83
    first = patch["edits"][0]
    assert set(first) == {
        "ID",
        "BallPos",
        "BallVector",
        "BallOwner",
        "PlayersInit",
        "TargetPoint",
    }
    assert first["ID"] == 101
