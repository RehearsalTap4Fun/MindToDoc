from pathlib import Path


HERE = Path(__file__).resolve().parent


def test_player_edit_controls_are_present_and_wired():
    html = (HERE / "index.html").read_text(encoding="utf-8")
    app = (HERE / "app.js").read_text(encoding="utf-8")

    for element_id in ("addHomePlayerButton", "addAwayPlayerButton", "deletePlayerButton"):
        assert f'id="{element_id}"' in html
        assert f"#{element_id}" in app

    for function_name in ("addPlayer", "deleteSelectedPlayer", "renumberPlayers"):
        assert f"function {function_name}" in app


def test_hit_testing_uses_nearest_candidate_for_overlapping_ball_and_player():
    app = (HERE / "app.js").read_text(encoding="utf-8")
    hit_test = app[app.index("function hitTest"):app.index("function onPointerDown")]

    assert "hitCandidates" in hit_test
    assert "distance / radius" in hit_test


def test_player_editing_does_not_add_patch_fields():
    app = (HERE / "app.js").read_text(encoding="utf-8")

    make_patch = app[app.index("function makePatch"):app.index("function patchKey")]
    assert "PlayersInit" in make_patch
    assert "AddPlayer" not in make_patch
    assert "DeletePlayer" not in make_patch
