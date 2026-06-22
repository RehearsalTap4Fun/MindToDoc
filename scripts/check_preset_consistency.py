#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preset 摆位合规检查(spec §6.1)。

加载主生成器最终 workbook,对每个 preset 断言协议 v1 §2-§5 约束:
1. BallPos / pos.z ∈ [-120, 0]
2. BallPos.x / pos.x ∈ [-18, 18]
3. BallPos.y ∈ [0, GOAL_HEIGHT]
4. 点球 preset(3, 9):BallPos == PENALTY_SPOT
5. 角球 preset(10, 11, 18):BallPos in {CORNER_LEFT_BALL, CORNER_RIGHT_BALL}
6. 守门 preset(4, 14, 15):home 玩家 pos.z ∈ [GOAL_AREA_Z_FAR, FIELD_Z_NEAR]
7. 任意球 preset(2, 7, 8, 17):防守墙连续两人 |Δx| ≥ WALL_PLAYER_GAP_MIN - 0.001
8. 方向、角度、枚举、JSON、控球索引、备注等基础字段均可解析且在约束内

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


def _workbook_presets() -> list[dict]:
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
        if row.get("ID") is not None:
            rows.append(row)
    return rows


def check_presets() -> list[str]:
    errors: list[str] = []
    presets = _workbook_presets()
    by_id = {p["ID"]: p for p in presets}
    valid_slice_types = set(g.SLICE_TYPE_NAME.values())
    valid_duties = set(g.PLAYER_AI_DUTY_ENUM.values())
    valid_modes = {"draw_line", "slingshot"}

    if len(by_id) != len(presets):
        errors.append("preset ID 存在重复")

    for p in presets:
        pid = p["ID"]
        if p.get("SliceType") not in valid_slice_types:
            errors.append(f"preset {pid} SliceType={p.get('SliceType')} 非法")

        bx, by_, bz = _parse_pos(p["BallPos"])

        if not (g.FIELD_Z_FAR <= bz <= g.FIELD_Z_NEAR):
            errors.append(f"preset {pid} BallPos.z={bz} 超出 [{g.FIELD_Z_FAR}, {g.FIELD_Z_NEAR}]")
        if not (-g.FIELD_X_HALF <= bx <= g.FIELD_X_HALF):
            errors.append(f"preset {pid} BallPos.x={bx} 超出 [±{g.FIELD_X_HALF}]")
        if not (0 <= by_ <= g.GOAL_HEIGHT):
            errors.append(f"preset {pid} BallPos.y={by_} 超出 [0, {g.GOAL_HEIGHT}]")

        vx, vy, vz = _parse_pos(p["BallVector"])
        if abs(vx) <= 1e-6 and abs(vy) <= 1e-6 and abs(vz) <= 1e-6:
            errors.append(f"preset {pid} BallVector 不能为零向量")
        for axis, value in (("x", vx), ("y", vy), ("z", vz)):
            if not (-1.0 <= value <= 1.0):
                errors.append(f"preset {pid} BallVector.{axis}={value} 超出 [-1, 1]")

        target = p.get("TargetPoint")
        if target:
            tx, ty, tz = _parse_pos(target)
            if not (-g.FIELD_X_HALF <= tx <= g.FIELD_X_HALF):
                errors.append(f"preset {pid} TargetPoint.x={tx} 超出 [±{g.FIELD_X_HALF}]")
            if not (0 <= ty <= g.GOAL_HEIGHT):
                errors.append(f"preset {pid} TargetPoint.y={ty} 超出 [0, {g.GOAL_HEIGHT}]")
            if not (g.FIELD_Z_FAR <= tz <= g.FIELD_Z_NEAR):
                errors.append(f"preset {pid} TargetPoint.z={tz} 超出 [{g.FIELD_Z_FAR}, {g.FIELD_Z_NEAR}]")

        players = json.loads(p["PlayersInit"])
        owner = int(p["BallOwner"])
        if not any(pl.get("team") == "home" and int(pl.get("idx", -1)) == owner for pl in players):
            errors.append(f"preset {pid} BallOwner={owner} 找不到对应 home 球员")

        seen_players: set[tuple[str, int]] = set()
        for pl in players:
            team = pl.get("team")
            idx = int(pl.get("idx", -1))
            duty = int(pl.get("duty", -1))
            if team not in {"home", "away"}:
                errors.append(f"preset {pid} player idx={idx} team={team} 非法")
            if duty not in valid_duties:
                errors.append(f"preset {pid} player(team={team},idx={idx}) duty={duty} 非法")
            key = (team, idx)
            if key in seen_players:
                errors.append(f"preset {pid} player(team={team},idx={idx}) 重复")
            seen_players.add(key)
            px = float(pl["pos"]["x"])
            py = float(pl["pos"]["y"])
            pz = float(pl["pos"]["z"])
            facing = float(pl["facing"])
            if not (-g.FIELD_X_HALF <= px <= g.FIELD_X_HALF):
                errors.append(f"preset {pid} player(team={team},idx={idx}) pos.x={px} 超出范围")
            if not (0 <= py <= g.GOAL_HEIGHT):
                errors.append(f"preset {pid} player(team={team},idx={idx}) pos.y={py} 超出范围")
            if not (g.FIELD_Z_FAR <= pz <= g.FIELD_Z_NEAR):
                errors.append(f"preset {pid} player(team={team},idx={idx}) pos.z={pz} 超出范围")
            if not (-180.0 <= facing <= 180.0):
                errors.append(f"preset {pid} player(team={team},idx={idx}) facing={facing} 超出范围")

        for field in ("CameraFov", "OperableAngle", "AngleSpanMin", "AngleSpanMax", "AngleMaxCenterShift", "AngleMargin"):
            try:
                float(p[field])
            except (TypeError, ValueError):
                errors.append(f"preset {pid} {field}={p.get(field)} 不是数字")

        if not (30.0 <= float(p["CameraFov"]) <= 70.0):
            errors.append(f"preset {pid} CameraFov={p['CameraFov']} 超出 [30, 70]")
        if not (0.0 <= float(p["OperableAngle"]) <= 180.0):
            errors.append(f"preset {pid} OperableAngle={p['OperableAngle']} 超出 [0, 180]")
        if not (0.0 <= float(p["AngleSpanMin"]) <= float(p["AngleSpanMax"]) <= 180.0):
            errors.append(f"preset {pid} AngleSpanMin/Max 非法")
        if not (0.0 <= float(p["AngleMaxCenterShift"]) <= 180.0):
            errors.append(f"preset {pid} AngleMaxCenterShift={p['AngleMaxCenterShift']} 超出 [0, 180]")
        if not (0.0 <= float(p["AngleMargin"]) <= 90.0):
            errors.append(f"preset {pid} AngleMargin={p['AngleMargin']} 超出 [0, 90]")

        if not isinstance(json.loads(p["Tags"]), list):
            errors.append(f"preset {pid} Tags 不是数组")
        if not isinstance(json.loads(p["TypePayload"]), dict):
            errors.append(f"preset {pid} TypePayload 不是对象")
        modes = set(json.loads(p["RecommendedModes"]))
        if not modes.issubset(valid_modes):
            errors.append(f"preset {pid} RecommendedModes={modes} 存在非法模式")
        if not isinstance(p.get("Remark"), str) or len(p["Remark"]) < 20:
            errors.append(f"preset {pid} Remark 过短或为空")

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
