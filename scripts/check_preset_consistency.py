#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preset 摆位合规检查(spec §6.1)。

加载主生成器 _build_presets,对每个 preset 断言协议 v1 §2-§5 约束:
1. BallPos / pos.z ∈ [-120, 0]
2. BallPos.x / pos.x ∈ [-18, 18]
3. BallPos.y ∈ [0, GOAL_HEIGHT]
4. 点球 preset(3, 9):BallPos == PENALTY_SPOT
5. 角球 preset(10, 11, 18):BallPos in {CORNER_LEFT_BALL, CORNER_RIGHT_BALL}
6. 守门 preset(4, 14, 15):home 玩家 pos.z ∈ [GOAL_AREA_Z_FAR, FIELD_Z_NEAR]
7. 任意球 preset(2, 7, 8, 17):防守墙连续两人 |Δx| ≥ WALL_PLAYER_GAP_MIN - 0.001

退出码 0 / 1 / 2(主生成器缺常量返回 2)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "output" / "test-config"))

import generate_activity_soccer_test_config as g  # noqa: E402

GAP_TOL = 1e-3


def _parse_pos(text: str) -> tuple[float, float, float]:
    d = json.loads(text)
    return float(d.get("x", 0)), float(d.get("y", 0)), float(d.get("z", 0))


def check_presets() -> list[str]:
    errors: list[str] = []
    lc = g.LcRegistry()
    presets = g._build_presets(lc)
    by_id = {p["ID"]: p for p in presets}

    for p in presets:
        pid = p["ID"]
        bx, by_, bz = _parse_pos(p["BallPos"])

        if not (g.FIELD_Z_FAR <= bz <= g.FIELD_Z_NEAR):
            errors.append(f"preset {pid} BallPos.z={bz} 超出 [{g.FIELD_Z_FAR}, {g.FIELD_Z_NEAR}]")
        if not (-g.FIELD_X_HALF <= bx <= g.FIELD_X_HALF):
            errors.append(f"preset {pid} BallPos.x={bx} 超出 [±{g.FIELD_X_HALF}]")
        if not (0 <= by_ <= g.GOAL_HEIGHT):
            errors.append(f"preset {pid} BallPos.y={by_} 超出 [0, {g.GOAL_HEIGHT}]")

        for pl in json.loads(p["PlayersInit"]):
            pz = float(pl["pos"]["z"])
            if not (g.FIELD_Z_FAR <= pz <= g.FIELD_Z_NEAR):
                errors.append(f"preset {pid} player(team={pl['team']},idx={pl['idx']}) pos.z={pz} 超出范围")

    for pid in (3, 9):
        if pid not in by_id:
            continue
        bx, _, bz = _parse_pos(by_id[pid]["BallPos"])
        if (bx, bz) != (g.PENALTY_SPOT[0], g.PENALTY_SPOT[2]):
            errors.append(f"preset {pid} BallPos 应在 PENALTY_SPOT={g.PENALTY_SPOT},实际 ({bx},{bz})")

    for pid in (10, 11, 18):
        if pid not in by_id:
            continue
        bx, _, bz = _parse_pos(by_id[pid]["BallPos"])
        ok = (bx, bz) in {(g.CORNER_LEFT_BALL[0], g.CORNER_LEFT_BALL[2]),
                          (g.CORNER_RIGHT_BALL[0], g.CORNER_RIGHT_BALL[2])}
        if not ok:
            errors.append(f"preset {pid} BallPos 不在角球点;实际 ({bx},{bz})")

    for pid in (4, 14, 15):
        if pid not in by_id:
            continue
        for pl in json.loads(by_id[pid]["PlayersInit"]):
            if pl["team"] == "home":
                pz = float(pl["pos"]["z"])
                if not (g.GOAL_AREA_Z_FAR <= pz <= g.FIELD_Z_NEAR):
                    errors.append(f"preset {pid}(守门) home 玩家 pos.z={pz} 不在小禁区 [{g.GOAL_AREA_Z_FAR}, {g.FIELD_Z_NEAR}]")

    for pid in (2, 7, 8, 17):
        if pid not in by_id:
            continue
        wall_xs = sorted(
            float(pl["pos"]["x"])
            for pl in json.loads(by_id[pid]["PlayersInit"])
            if pl["team"] == "away" and pl["duty"] == g.PLAYER_AI_DUTY_ENUM["Defender"]
        )
        for a, b in zip(wall_xs, wall_xs[1:]):
            if (b - a) < g.WALL_PLAYER_GAP_MIN - GAP_TOL:
                errors.append(f"preset {pid} 任意球人墙 Δx={b-a:.2f} < {g.WALL_PLAYER_GAP_MIN} (球员重叠或球穿不过)")

    return errors


def main() -> int:
    try:
        errors = check_presets()
    except AttributeError as e:
        print(f"[error] 主生成器缺少协议常量(尚未重构?): {e}", file=sys.stderr)
        return 2

    if errors:
        print(f"[FAIL] {len(errors)} 处违规:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"[ok] 18 preset 全部合规")
    return 0


if __name__ == "__main__":
    sys.exit(main())
