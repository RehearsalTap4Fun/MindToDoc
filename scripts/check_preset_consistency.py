#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preset 摆位合规检查(spec §6.1)。

加载主生成器最终 workbook,对每个 preset 断言协议 v1 §2-§5 约束:
1. BallPos / pos.z ∈ [-120, 0]
2. BallPos.x / pos.x ∈ [-18, 18]
3. BallPos.y ∈ [0, GOAL_HEIGHT]
4. 点球 preset:BallPos == PENALTY_SPOT
5. 角球 preset:BallPos in {CORNER_LEFT_BALL, CORNER_RIGHT_BALL}
6. 守门 preset:home 玩家 pos.z ∈ [GOAL_AREA_Z_FAR, FIELD_Z_NEAR]
7. 任意球 preset:防守墙连续两人 |Δx| ≥ WALL_PLAYER_GAP_MIN - 0.001
8. 方向、角度、枚举、JSON、控球索引、备注等基础字段均可解析且在约束内
9. 对方门将(away.duty=Goalkeeper) z 取值必须落在三档常量之一,且与切片类型一致
10. 主生成器源代码中 keeper z 不得散布硬编码,必须通过 away_keeper_z()/常量取

退出码 0 / 1 / 2(主生成器缺常量返回 2)。
"""
from __future__ import annotations

import ast
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

    for p in presets:
        if p["SliceType"] != "penalty":
            continue
        pid = p["ID"]
        bx, _, bz = _parse_pos(p["BallPos"])
        if (bx, bz) != (g.PENALTY_SPOT[0], g.PENALTY_SPOT[2]):
            errors.append(f"preset {pid} BallPos 应在 PENALTY_SPOT={g.PENALTY_SPOT},实际 ({bx},{bz})")

    for p in presets:
        if p["SliceType"] != "corner":
            continue
        pid = p["ID"]
        bx, _, bz = _parse_pos(p["BallPos"])
        ok = (bx, bz) in {(g.CORNER_LEFT_BALL[0], g.CORNER_LEFT_BALL[2]),
                          (g.CORNER_RIGHT_BALL[0], g.CORNER_RIGHT_BALL[2])}
        if not ok:
            errors.append(f"preset {pid} BallPos 不在角球点;实际 ({bx},{bz})")

    for p in presets:
        if p["SliceType"] != "goalkeep":
            continue
        pid = p["ID"]
        for pl in json.loads(p["PlayersInit"]):
            if pl["team"] == "home":
                pz = float(pl["pos"]["z"])
                if not (g.GOAL_AREA_Z_FAR <= pz <= g.FIELD_Z_NEAR):
                    errors.append(f"preset {pid}(守门) home 玩家 pos.z={pz} 不在小禁区 [{g.GOAL_AREA_Z_FAR}, {g.FIELD_Z_NEAR}]")

    for p in presets:
        if p["SliceType"] != "free_kick":
            continue
        pid = p["ID"]
        wall_xs = sorted(
            float(pl["pos"]["x"])
            for pl in json.loads(p["PlayersInit"])
            if pl["team"] == "away" and pl["duty"] == g.PLAYER_AI_DUTY_ENUM["Defender"]
        )
        for a, b in zip(wall_xs, wall_xs[1:]):
            if (b - a) < g.WALL_PLAYER_GAP_MIN - GAP_TOL:
                errors.append(f"preset {pid} 任意球人墙 Δx={b-a:.2f} < {g.WALL_PLAYER_GAP_MIN} (球员重叠或球穿不过)")

    for p in presets:
        pid = p["ID"]
        stype = p["SliceType"]
        keeper_zs = [
            float(pl["pos"]["z"])
            for pl in json.loads(p["PlayersInit"])
            if pl["team"] == "away" and pl["duty"] == g.PLAYER_AI_DUTY_ENUM["Goalkeeper"]
        ]
        if not keeper_zs:
            continue
        allowed = {g.AWAY_KEEPER_Z_DEFAULT, g.AWAY_KEEPER_Z_PENALTY, g.AWAY_KEEPER_Z_LONG_ATTACK}
        for kz in keeper_zs:
            if kz not in allowed:
                errors.append(
                    f"preset {pid} 对方门将 z={kz} 不在三档常量 {sorted(allowed)}"
                )
                continue
            bz = _parse_pos(p["BallPos"])[2]
            expect = g.away_keeper_z(stype, bz)
            if kz != expect:
                errors.append(
                    f"preset {pid} ({stype}, ball_z={bz}) 对方门将 z={kz} 与档位规则期望 {expect} 不符"
                )

    return errors


KEEPER_Z_ALLOWED_NAMES = {
    "AWAY_KEEPER_Z_DEFAULT",
    "AWAY_KEEPER_Z_PENALTY",
    "AWAY_KEEPER_Z_LONG_ATTACK",
}


def _is_keeper_init_call(call: ast.Call) -> bool:
    if not (isinstance(call.func, ast.Name) and call.func.id == "player_init"):
        return False
    if len(call.args) < 6:
        return False
    team_arg = call.args[0]
    duty_arg = call.args[2]
    if not (isinstance(team_arg, ast.Constant) and team_arg.value == "away"):
        return False
    if isinstance(duty_arg, ast.Subscript):
        # PLAYER_AI_DUTY_ENUM["Goalkeeper"]
        sl = duty_arg.slice
        if isinstance(sl, ast.Constant) and sl.value == "Goalkeeper":
            return True
    return False


def _z_arg_is_allowed(z_node: ast.AST) -> bool:
    """允许:常量 0(占位) / AWAY_KEEPER_Z_* 常量名 / away_keeper_z(...) 调用 / 局部 keeper_z 变量。"""
    if isinstance(z_node, ast.Constant) and z_node.value == 0:
        return True  # 0 同时是 PENALTY 档常量值,放行
    if isinstance(z_node, ast.Name):
        if z_node.id in KEEPER_Z_ALLOWED_NAMES:
            return True
        if z_node.id == "keeper_z":
            return True  # helper 内部局部变量,helper 自己取自 away_keeper_z()
        return False
    if isinstance(z_node, ast.Call):
        if isinstance(z_node.func, ast.Name) and z_node.func.id == "away_keeper_z":
            return True
    return False


def check_keeper_z_hardcode() -> list[str]:
    """扫主生成器源代码:player_init(..., Goalkeeper, x, y, <z>, ...) 中第 6 参 z
    必须是 away_keeper_z()/AWAY_KEEPER_Z_* 常量/局部 keeper_z 变量,
    禁止散布数字字面量(0 例外:它本身就是 PENALTY 档值)。"""
    src_path = ROOT / "output" / "test-config" / "generate_activity_soccer_test_config.py"
    text = src_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(src_path))
    errors: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_keeper_init_call(node):
            continue
        z_node = node.args[5]
        if _z_arg_is_allowed(z_node):
            continue
        snippet = ast.unparse(z_node)
        errors.append(
            f"{src_path.name}:{node.lineno} 对方门将 z 参数 `{snippet}` 不合规;"
            f"应为 away_keeper_z(slice_type, ball_z) / AWAY_KEEPER_Z_* / keeper_z 局部变量"
        )
    return errors


def main() -> int:
    try:
        errors = check_presets()
        errors.extend(check_keeper_z_hardcode())
    except AttributeError as e:
        print(f"[error] 主生成器缺少协议常量(尚未重构?): {e}", file=sys.stderr)
        return 2

    if errors:
        print(f"[FAIL] {len(errors)} 处违规:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"[ok] {len(_workbook_presets())} preset 全部合规")
    return 0


if __name__ == "__main__":
    sys.exit(main())
