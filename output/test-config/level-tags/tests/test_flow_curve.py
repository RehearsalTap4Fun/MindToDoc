import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))


def test_recommended_curve_has_target_coverage_and_valid_tags():
    import generate_recommended_flow_tags as flow
    import level_tag_lib

    rows = flow.build_recommended_rows()
    tagged = [r for r in rows if r["Tags"]]
    coverage = len(tagged) / len(rows)
    assert 0.60 <= coverage <= 0.70

    registry = set(level_tag_lib.TAG_REGISTRY)
    for row in tagged:
        assert set(row["Tags"]).issubset(registry)
        assert row["Note"]


def test_recommended_curve_has_boss_checks_at_round_ends():
    import generate_recommended_flow_tags as flow

    rows = {r["ID"]: r for r in flow.build_recommended_rows()}
    for level_id in (50, 100, 150, 200, 250, 300, 350, 400, 450, 500):
        assert "boss" in rows[level_id]["Tags"]


def test_recommended_curve_keeps_recovery_slots_in_each_round():
    import generate_recommended_flow_tags as flow

    rows = flow.build_recommended_rows()
    for round_id in range(1, 51):
        round_rows = [r for r in rows if r["Round"] == round_id]
        assert any("恢复" in r["Note"] for r in round_rows)


def test_recommended_curve_does_not_combine_short_match_with_lenient():
    import generate_recommended_flow_tags as flow

    for row in flow.build_recommended_rows():
        tags = set(row["Tags"])
        assert not {"short_match", "lenient"}.issubset(tags)
