# Soccer Preset Expansion Design

## Goal

Expand the World Cup soccer level foundation from a small test preset set into a production candidate library with 50 base presets and richer, perceivable slice instance variants.

## Preset Distribution

The base preset library must contain exactly 50 rows:

| SliceType | Count | Design intent |
|---|---:|---|
| attack | 14 | Main perceptual variety: lane, distance, angle, lob, cut-in, assist and rebound-like setups |
| free_kick | 9 | Wall, distance, side, curve and cross-oriented set pieces |
| penalty | 5 | Minimal but distinct target/pressure variants |
| corner | 10 | High-value variety: left/right, near/far/center, short corner, low cross and scramble |
| throw_in | 8 | Sideline restart variety: near support, far switch, quick counter, box-edge attack |
| goalkeep | 4 | Kept intentionally small; variation should come mostly from AI/reaction/modifiers |

## Instance Variant Rules

`ActvSoccerSliceInstanceCfg` must expose variation players can notice, not just numeric duplication.

- Each non-legacy tier/type combination should have at least 3 variants.
- Variant 1 is direct scoring/survival.
- Variant 2 is the established pressured or compound variant. Existing tags may continue to force v2.
- Variant 3 is a spatial variant that picks a different preset from the same SliceType pool.
- `attack`, `corner`, and `throw_in` may use `pass_to + score` compound objectives when the preset contains a receiving teammate.
- `penalty` and `goalkeep` keep `OverrideOperableAngle = 0`.
- `narrow_angle` must not apply to `penalty` or `goalkeep`; those types have no operable angle to shrink.

## Validation

The generator and tag output must pass:

- `python -m pytest output/test-config/level-tags/tests/ -q`
- `python scripts/check_preset_consistency.py`
- `$env:PYTHONIOENCODING='utf-8'; python scripts/check_protocol_drift.py`
- `python output/test-config/generate_activity_soccer_test_config.py`
- `python output/test-config/level-tags/apply_level_tags.py`
- `python scripts/check_xlsx_drift.py --summary`

