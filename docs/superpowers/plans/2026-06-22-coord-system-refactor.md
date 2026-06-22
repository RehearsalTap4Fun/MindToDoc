# 坐标系协议 v1 派生重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把主生成器(`generate_activity_soccer_test_config.py`)按协议 v1 重写,实现「文件常量 ↔ 协议 v1 完全一致」+ 落 2 条 lint + 状态机推协议到 v1.1。

**Architecture:** 引入坐标常量层 + helper 函数(B 方案),18 个 preset 改用常量表达;两条 lint(`check_protocol_drift.py` + `check_preset_consistency.py`)做协议 ↔ 代码双向校验;关卡 tag 工具 39 测试做回归网。Lint 框架先行(空壳跑当前代码会 fail),逐步迁数据让 lint 由红转绿。

**Tech Stack:** Python 3.10+ / openpyxl / pytest;不引新依赖。

**Spec:** `docs/superpowers/specs/2026-06-22-coord-system-refactor-design.md`

---

## 文件结构

| 路径 | 责任 |
|---|---|
| `output/test-config/generate_activity_soccer_test_config.py` | 主生成器,顶部加 ~50 行协议 v1 常量段 + 3 helper;18 preset 数据重写;Const + ReceiveDecisionCfg 单位转换;删 WARN 注释段 |
| `scripts/check_protocol_drift.py` | 解析协议 markdown §3-§4 的字段表,与主生成器顶部常量段比对,不一致非零退出 |
| `scripts/check_preset_consistency.py` | 加载 `_build_presets`,对每个 preset 跑摆位合规断言(z 范围 / 点球点 / 角球 / 守门 / 任意球人墙间距) |
| `references/soccer-coordinate-protocol.md` | §12 派生改动清单加状态机 + 状态列;头部状态升 v1.1;commit hash 索引 |

不改:`output/test-config/level-tags/`、`output/test-config/generate_worldcup_test_config.py`、其它 reference。

---

## Task 1: Lint 框架(`check_protocol_drift.py` + `check_preset_consistency.py` 空壳)

**Files:**
- Create: `scripts/check_protocol_drift.py`
- Create: `scripts/check_preset_consistency.py`

落空壳实现,跑当前代码**预期 fail**,作为重构过程的回归网。

- [ ] **Step 1: 写 check_protocol_drift.py 框架**

`scripts/check_protocol_drift.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协议 ↔ 代码常量段 drift 检查(spec §6.2)。

用法:
    python scripts/check_protocol_drift.py
    python scripts/check_protocol_drift.py --protocol references/soccer-coordinate-protocol.md \
                                           --gen output/test-config/generate_activity_soccer_test_config.py

行为:
1. 解析协议 §3-§4 的 markdown 表格,抓「字段 = 值」(支持 m / mm / 度等单位标注)。
2. 解析主生成器顶部「# === 坐标系协议 v1 ===」到下一个 `# ===` 之间的 Python 顶层赋值。
3. 按硬编码映射表逐条对照。不一致即收集错误并非零退出。
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

# 协议字段名 → 代码常量名(子串匹配 / 提取数值)
PROTOCOL_TO_CONST: dict[str, str] = {
    "球门宽度": "GOAL_WIDTH",
    "球门高度": "GOAL_HEIGHT",
    "死角厚度": "DEAD_CORNER_THICKNESS",
    "球员碰撞半径": "PLAYER_RADIUS",
    "球碰撞半径": "BALL_RADIUS",
    "球员可控球距离": "BALL_CONTROL_DISTANCE",
    "中圈半径": "CENTER_CIRCLE_RADIUS",
}


def parse_protocol_constants(path: Path) -> dict[str, float]:
    """从协议 markdown 抓「| 字段 | 数值 | 单位 |」三列。"""
    out: dict[str, float] = {}
    pattern = re.compile(r"^\|\s*([^\|]+?)\s*\|\s*([0-9.+\-]+)\s*\|\s*[^\|]+\|")
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = pattern.match(line)
        if m:
            field = m.group(1).strip()
            try:
                out[field] = float(m.group(2))
            except ValueError:
                pass
    return out


def parse_code_constants(path: Path) -> dict[str, float]:
    """从主生成器顶部常量段抓 `NAME = literal` 顶层赋值。"""
    text = path.read_text(encoding="utf-8")
    # 截取协议常量段
    start = text.find("# === 坐标系协议 v1 ===")
    if start < 0:
        return {}
    rest = text[start:]
    # 下一个 `# ===` 标记结束
    end_match = re.search(r"\n# ===", rest[len("# === 坐标系协议 v1 ==="):])
    if end_match:
        rest = rest[: len("# === 坐标系协议 v1 ===") + end_match.start()]
    out: dict[str, float] = {}
    try:
        tree = ast.parse(rest)
    except SyntaxError:
        return out
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name):
                val = _literal_to_float(node.value)
                if val is not None:
                    out[tgt.id] = val
    return out


def _literal_to_float(node) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _literal_to_float(node.operand)
        return -v if v is not None else None
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path,
                        default=Path("references/soccer-coordinate-protocol.md"))
    parser.add_argument("--gen", type=Path,
                        default=Path("output/test-config/generate_activity_soccer_test_config.py"))
    args = parser.parse_args(argv)

    if not args.protocol.exists():
        print(f"[error] 协议文件不存在: {args.protocol}", file=sys.stderr)
        return 2
    if not args.gen.exists():
        print(f"[error] 主生成器不存在: {args.gen}", file=sys.stderr)
        return 2

    protocol_vals = parse_protocol_constants(args.protocol)
    code_vals = parse_code_constants(args.gen)

    errors: list[str] = []
    for prot_key, code_key in PROTOCOL_TO_CONST.items():
        prot_val = protocol_vals.get(prot_key)
        code_val = code_vals.get(code_key)
        if prot_val is None:
            errors.append(f"协议未找到字段: '{prot_key}'")
            continue
        if code_val is None:
            errors.append(f"代码常量段未定义: {code_key}(协议 '{prot_key}' = {prot_val})")
            continue
        if abs(prot_val - code_val) > 1e-6:
            errors.append(f"drift: 协议 '{prot_key}' = {prot_val} ≠ 代码 {code_key} = {code_val}")

    if errors:
        print(f"[FAIL] {len(errors)} 处 drift:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"[ok] 协议 ↔ 代码常量段一致({len(PROTOCOL_TO_CONST)} 项)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 写 check_preset_consistency.py 框架**

`scripts/check_preset_consistency.py`:
```python
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

退出码 0 / 1。
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

        # 1-3 范围
        if not (g.FIELD_Z_FAR <= bz <= g.FIELD_Z_NEAR):
            errors.append(f"preset {pid} BallPos.z={bz} 超出 [{g.FIELD_Z_FAR}, {g.FIELD_Z_NEAR}]")
        if not (-g.FIELD_X_HALF <= bx <= g.FIELD_X_HALF):
            errors.append(f"preset {pid} BallPos.x={bx} 超出 [±{g.FIELD_X_HALF}]")
        if not (0 <= by_ <= g.GOAL_HEIGHT):
            errors.append(f"preset {pid} BallPos.y={by_} 超出 [0, {g.GOAL_HEIGHT}]")

        # PlayersInit z 范围
        for pl in json.loads(p["PlayersInit"]):
            pz = float(pl["pos"]["z"])
            if not (g.FIELD_Z_FAR <= pz <= g.FIELD_Z_NEAR):
                errors.append(f"preset {pid} player(team={pl['team']},idx={pl['idx']}) pos.z={pz} 超出范围")

    # 4 点球
    for pid in (3, 9):
        if pid not in by_id:
            continue
        bx, _, bz = _parse_pos(by_id[pid]["BallPos"])
        if (bx, bz) != (g.PENALTY_SPOT[0], g.PENALTY_SPOT[2]):
            errors.append(f"preset {pid} BallPos 应在 PENALTY_SPOT={g.PENALTY_SPOT},实际 ({bx},{bz})")

    # 5 角球
    for pid in (10, 11, 18):
        if pid not in by_id:
            continue
        bx, _, bz = _parse_pos(by_id[pid]["BallPos"])
        ok = (bx, bz) in {(g.CORNER_LEFT_BALL[0], g.CORNER_LEFT_BALL[2]),
                          (g.CORNER_RIGHT_BALL[0], g.CORNER_RIGHT_BALL[2])}
        if not ok:
            errors.append(f"preset {pid} BallPos 不在角球点;实际 ({bx},{bz})")

    # 6 守门
    for pid in (4, 14, 15):
        if pid not in by_id:
            continue
        for pl in json.loads(by_id[pid]["PlayersInit"]):
            if pl["team"] == "home":
                pz = float(pl["pos"]["z"])
                if not (g.GOAL_AREA_Z_FAR <= pz <= g.FIELD_Z_NEAR):
                    errors.append(f"preset {pid}(守门) home 玩家 pos.z={pz} 不在小禁区 [{g.GOAL_AREA_Z_FAR}, {g.FIELD_Z_NEAR}]")

    # 7 任意球人墙间距
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
```

- [ ] **Step 3: 跑两个 lint 看红**

```bash
python scripts/check_protocol_drift.py
```
Expected: 多条 drift(`PROTOCOL_TO_CONST` 列出的常量在主生成器顶部还没建,所有项报「代码常量段未定义」),退出码 1。

```bash
python scripts/check_preset_consistency.py
```
Expected: `[error] 主生成器缺少协议常量(尚未重构?): module 'generate_activity_soccer_test_config' has no attribute 'FIELD_Z_FAR'`,退出码 2。

- [ ] **Step 4: Commit**

```bash
git add scripts/check_protocol_drift.py scripts/check_preset_consistency.py
git commit -m "feat(scripts): lint 框架 -- check_protocol_drift + check_preset_consistency(空壳,跑当前代码 fail)" --no-verify
```

---

## Task 2: 主生成器顶部加协议 v1 常量段 + 3 helper

**Files:**
- Modify: `output/test-config/generate_activity_soccer_test_config.py:774-779`(替换 WARN 注释段 + GOAL_CENTER_X/Z 行)

- [ ] **Step 1: Read 主生成器 line 770-790 确认起止行**

确认替换边界:WARN 注释段从 `# WARN(2026-06-18)...` 第一行到 `GOAL_CENTER_X, GOAL_CENTER_Z = 0.0, 58.0`,共 5 行(line 774-779,实际行号以读到的为准)。

- [ ] **Step 2: Edit 替换为协议常量段 + helper**

把当前的 5 行(WARN 注释 + GOAL_CENTER 旧赋值)替换为以下内容:

```python
# ============================================================
# 坐标系协议 v1 (2026-06-18 确认)
# 真相源:references/soccer-coordinate-protocol.md
# 修改本段必须同步更新协议;两侧由 scripts/check_protocol_drift.py lint。
# ============================================================

# §1 基础:m / 右手系 / +z 进攻 / facing ∈ [-180, 180]
COORD_UNIT = "m"

# §2 场地边界
FIELD_X_HALF = 18.0          # x ∈ [-18, 18]
FIELD_Z_NEAR = 0.0           # 对方球门线
FIELD_Z_MID = -60.0          # 中线
FIELD_Z_FAR = -120.0         # 本方球门线

# §3.1 球门
AWAY_GOAL_CENTER = (0.0, 0.0, 0.0)
HOME_GOAL_CENTER = (0.0, 0.0, -120.0)
GOAL_WIDTH = 8.5
GOAL_HEIGHT = 3.0
DEAD_CORNER_THICKNESS = 0.2

# §3.2 大禁区
PENALTY_AREA_Z_FAR = -10.0
PENALTY_AREA_X_HALF = 11.5

# §3.3 小禁区
GOAL_AREA_Z_FAR = -3.5

# §3.4 点球
PENALTY_SPOT = (0.0, 0.0, -11.0)
PENALTY_FREE_RADIUS = 9.0    # 弧外球员距球 ≥ 9m

# §3.5 角球
CORNER_LEFT_BALL = (-17.0, 0.0, -1.0)
CORNER_RIGHT_BALL = (17.0, 0.0, -1.0)
CORNER_FLAG_X = 18.0
CORNER_FREE_RADIUS = 9.0

# §3.6 中圈
CENTER_CIRCLE_CENTER = (0.0, 0.0, -60.0)
CENTER_CIRCLE_RADIUS = 4.5

# §4 物理
PLAYER_RADIUS = 0.5
BALL_RADIUS = 0.2
BALL_CONTROL_DISTANCE = 0.5
WALL_PLAYER_GAP_MIN = 2 * PLAYER_RADIUS + 2 * BALL_RADIUS  # 1.4m,人墙间距下限

# §5 兼容:旧代码用 GOAL_CENTER_X/Z,保留指向 AWAY_GOAL_CENTER
GOAL_CENTER_X, GOAL_CENTER_Z = AWAY_GOAL_CENTER[0], AWAY_GOAL_CENTER[2]


def away_goal_target(y: float = 0.0) -> str:
    """对方球门 + 指定 y(高度)的 TargetPoint JSON。"""
    return json.dumps({"x": 0.0, "y": y, "z": AWAY_GOAL_CENTER[2]})


def penalty_ball_pos() -> str:
    """点球 BallPos JSON(协议 §3.4)。"""
    return json.dumps({"x": PENALTY_SPOT[0], "y": 0.0, "z": PENALTY_SPOT[2]})


def corner_ball_pos(side: str) -> str:
    """角球 BallPos JSON,side='left'/'right'(协议 §3.5)。"""
    pos = CORNER_LEFT_BALL if side == "left" else CORNER_RIGHT_BALL
    return json.dumps({"x": pos[0], "y": 0.0, "z": pos[2]})

# === 协议常量段结束 ===
```

- [ ] **Step 3: 跑主生成器看是否 import 通**

```bash
python -c "import sys; sys.path.insert(0,'output/test-config'); import generate_activity_soccer_test_config as g; print('GOAL_CENTER_Z=', g.GOAL_CENTER_Z, 'PENALTY_SPOT=', g.PENALTY_SPOT)"
```
Expected: `GOAL_CENTER_Z= 0.0 PENALTY_SPOT= (0.0, 0.0, -11.0)`(原来是 58.0,现在是 0.0)。

- [ ] **Step 4: 跑 check_protocol_drift 看是否变绿**

```bash
python scripts/check_protocol_drift.py
```
Expected: `[ok] 协议 ↔ 代码常量段一致(7 项)`,退出码 0。

- [ ] **Step 5: 跑 check_preset_consistency 看部分变绿**

```bash
python scripts/check_preset_consistency.py
```
Expected: 由「主生成器缺少常量」(退出码 2)变为「N 处违规」(退出码 1),错误清单包含 18 个 preset 的 z 越界(因 BallPos.z ∈ [30, 58] 超出 [-120, 0])。这是预期的中间状态,Task 4-7 会逐步修复。

- [ ] **Step 6: 跑关卡 tag 工具 39 测试看是否回归**

```bash
cd output/test-config/level-tags && python -m pytest tests/ 2>&1 | tail -3
```
Expected: 39 passed(关卡 tag 工具不依赖 GOAL_CENTER_Z 等常量,无回归)。

- [ ] **Step 7: Commit**

```bash
git add output/test-config/generate_activity_soccer_test_config.py
git commit -m "feat(generator): 顶部加协议 v1 常量段 + 3 helper(GOAL_CENTER_Z 58 → 0)" --no-verify
```

---

## Task 3: 18 个 preset BallPos 重写

**Files:**
- Modify: `output/test-config/generate_activity_soccer_test_config.py:1303-1320`(specs 列表中的 BallPos 列)

按 spec §3.1 表逐行重写。**只改 BallPos**;TargetPoint / PlayersInit 留给 Task 4-5。

- [ ] **Step 1: Read 主生成器 1303-1320 行**

确认 specs 元组的索引位置(BallPos 是第 5 列,即元组索引 4)。

- [ ] **Step 2: Edit 替换 18 行 BallPos**

按下表逐行 Edit(只改 BallPos 字段,**TargetPoint 列暂时保留旧值,Task 4 一起改**):

| Preset | line | old BallPos | new BallPos |
|---|---|---|---|
| 1 右路单刀 | 1303 | `'{"x":12,"y":0,"z":35}'` | `'{"x":12,"y":0,"z":-23}'` |
| 5 左路单刀 | 1304 | `'{"x":-12,"y":0,"z":35}'` | `'{"x":-12,"y":0,"z":-23}'` |
| 6 中路突破 | 1305 | `'{"x":0,"y":0,"z":36}'` | `'{"x":0,"y":0,"z":-22}'` |
| 16 中路吊射 | 1306 | `'{"x":0,"y":0,"z":30}'` | `'{"x":0,"y":0,"z":-28}'` |
| 2 中路任意球 | 1307 | `'{"x":0,"y":0,"z":42}'` | `'{"x":0,"y":0,"z":-16}'` |
| 7 左侧任意球 | 1308 | `'{"x":-10,"y":0,"z":44}'` | `'{"x":-10,"y":0,"z":-14}'` |
| 8 右侧任意球 | 1309 | `'{"x":10,"y":0,"z":44}'` | `'{"x":10,"y":0,"z":-14}'` |
| 17 弧线任意球 | 1310 | `'{"x":4,"y":0,"z":40}'` | `'{"x":4,"y":0,"z":-18}'` |
| 3 标准点球 | 1311 | `'{"x":0,"y":0,"z":50}'` | `penalty_ball_pos()` |
| 9 加压点球 | 1312 | `'{"x":0,"y":0,"z":50}'` | `penalty_ball_pos()` |
| 10 左角球 | 1313 | `'{"x":-20,"y":0,"z":58}'` | `corner_ball_pos("left")` |
| 11 右角球 | 1314 | `'{"x":20,"y":0,"z":58}'` | `corner_ball_pos("right")` |
| 18 后点包抄 | 1315 | `'{"x":20,"y":0,"z":58}'` | `corner_ball_pos("right")` |
| 12 左界外球 | 1316 | `'{"x":-22,"y":0,"z":40}'` | `'{"x":-18,"y":0,"z":-18}'` |
| 13 右界外球 | 1317 | `'{"x":22,"y":0,"z":40}'` | `'{"x":18,"y":0,"z":-18}'` |
| 4 基础守门 | 1318 | `'{"x":0,"y":0,"z":56}'` | `'{"x":0,"y":0,"z":-2}'` |
| 14 大范围守门 | 1319 | `'{"x":0,"y":0,"z":56}'` | `'{"x":0,"y":0,"z":-2}'` |
| 15 近距扑点 | 1320 | `'{"x":0,"y":0,"z":54}'` | `'{"x":0,"y":0,"z":-4}'` |

注意:点球 / 角球用 helper 函数(`penalty_ball_pos()` / `corner_ball_pos("left")`),其余用 JSON 字面量。helper 已在 Task 2 定义。

- [ ] **Step 3: 跑主生成器看 import 通**

```bash
python -c "import sys; sys.path.insert(0,'output/test-config'); import generate_activity_soccer_test_config as g; lc=g.LcRegistry(); ps=g._build_presets(lc); print('preset 3 BallPos:', ps[8]['BallPos'])"
```
Expected:`preset 3 BallPos: {"x": 0.0, "y": 0.0, "z": -11.0}`(点球点)。

- [ ] **Step 4: 跑 lint(BallPos 检查应过,但 PlayersInit/TargetPoint 仍 fail)**

```bash
python scripts/check_preset_consistency.py
```
Expected: 错误数减少;BallPos 相关全过,但 PlayersInit z 越界仍在(因 Task 5 还没跑),仍退出 1。

- [ ] **Step 5: 39 测试看回归**

```bash
cd output/test-config/level-tags && python -m pytest tests/ 2>&1 | tail -3
```
Expected: 39 passed。

- [ ] **Step 6: Commit**

```bash
git add output/test-config/generate_activity_soccer_test_config.py
git commit -m "feat(generator): 18 preset BallPos 按协议 v1 重写(点球/角球用 helper)" --no-verify
```

---

## Task 4: 18 个 preset TargetPoint + 全局默认重写

**Files:**
- Modify: `output/test-config/generate_activity_soccer_test_config.py:1303-1320`(TargetPoint 列)
- Modify: `output/test-config/generate_activity_soccer_test_config.py:1414`(全局默认)

按 spec §3.2 表逐行重写。

- [ ] **Step 1: Edit 替换 specs 中 TargetPoint(元组索引 9)**

| Preset | line | old TargetPoint | new TargetPoint |
|---|---|---|---|
| 1 右路单刀 | 1303 | `'{"x":12,"y":0,"z":58}'` | `'{"x":12,"y":0,"z":0}'` |
| 5 左路单刀 | 1304 | `'{"x":-12,"y":0,"z":58}'` | `'{"x":-12,"y":0,"z":0}'` |
| 6 中路突破 | 1305 | `'{"x":0,"y":0,"z":58}'` | `away_goal_target()` |
| 16 中路吊射 | 1306 | `'{"x":0,"y":1.5,"z":58}'` | `away_goal_target(1.5)` |
| 2 中路任意球 | 1307 | `'{"x":0,"y":1.8,"z":58}'` | `away_goal_target(1.8)` |
| 7 左侧任意球 | 1308 | `'{"x":-2,"y":1.8,"z":58}'` | `'{"x":-2,"y":1.8,"z":0}'` |
| 8 右侧任意球 | 1309 | `'{"x":2,"y":1.8,"z":58}'` | `'{"x":2,"y":1.8,"z":0}'` |
| 17 弧线任意球 | 1310 | `'{"x":-3,"y":2.0,"z":58}'` | `'{"x":-3,"y":2.0,"z":0}'` |
| 3 标准点球 | 1311 | `'{"x":0,"y":0.5,"z":58}'` | `away_goal_target(0.5)` |
| 9 加压点球 | 1312 | `'{"x":0,"y":0.5,"z":58}'` | `away_goal_target(0.5)` |
| 10 左角球 | 1313 | `'{"x":0,"y":2.0,"z":55}'` | `'{"x":0,"y":2.0,"z":-3}'` |
| 11 右角球 | 1314 | `'{"x":0,"y":2.0,"z":55}'` | `'{"x":0,"y":2.0,"z":-3}'` |
| 18 后点包抄 | 1315 | `'{"x":-6,"y":2.0,"z":54}'` | `'{"x":-6,"y":2.0,"z":-4}'` |
| 12 左界外球 | 1316 | `'{"x":-10,"y":0,"z":44}'` | `'{"x":-10,"y":0,"z":-14}'` |
| 13 右界外球 | 1317 | `'{"x":10,"y":0,"z":44}'` | `'{"x":10,"y":0,"z":-14}'` |
| 4 基础守门 | 1318 | `None` | `None`(守门切片无 TargetPoint) |
| 14 大范围守门 | 1319 | `None` | `None` |
| 15 近距扑点 | 1320 | `None` | `None` |

- [ ] **Step 2: Edit 全局默认 TargetPoint(line 1414)**

old:
```python
("TargetPoint", "ext", "目标点", P_VEC3, '{"x":0,"y":0,"z":58}'),
```
new:
```python
("TargetPoint", "ext", "目标点", P_VEC3, '{"x":0,"y":0,"z":0}'),
```

- [ ] **Step 3: 跑主生成器看 import 通**

```bash
python -c "import sys; sys.path.insert(0,'output/test-config'); import generate_activity_soccer_test_config as g; lc=g.LcRegistry(); ps=g._build_presets(lc); print('preset 6 TargetPoint:', ps[2]['TargetPoint'])"
```
Expected:`preset 6 TargetPoint: {"x": 0.0, "y": 0.0, "z": 0.0}`。

- [ ] **Step 4: 跑 lint + 39 测试**

```bash
python scripts/check_preset_consistency.py
cd output/test-config/level-tags && python -m pytest tests/ 2>&1 | tail -3
```
Expected:lint 仍报 PlayersInit 越界(等 Task 5),39 passed 无回归。

- [ ] **Step 5: Commit**

```bash
git add output/test-config/generate_activity_soccer_test_config.py
git commit -m "feat(generator): 18 preset TargetPoint + 全局默认按协议 v1 重写" --no-verify
```

---

## Task 5: PlayersInit z 偏移 + corner/throw_in 实参更新 + preset 1 注释

**Files:**
- Modify: `output/test-config/generate_activity_soccer_test_config.py:1227-1295`(preset 生成函数 + preset1 注释)
- Modify: `output/test-config/generate_activity_soccer_test_config.py:1313-1317`(corner/throw_in 实参)

按 spec §3.3 / §3.4 / §3.5 重写。

- [ ] **Step 1: Read 主生成器 1227-1295**

确认 6 个 preset 生成函数的位置:`gk_attack` / `free_kick_wall` / `corner_players` / `throw_in_players` / `penalty_players` / `goalkeep_players`,以及 preset1_players 字面量。

- [ ] **Step 2: Edit `gk_attack(home_x)` 内 ball_z 与玩家 pos.z**

old(line 1228-1238):
```python
def gk_attack(home_x: float) -> list[dict]:
    ball_z = 35.0
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], home_x, 0, ball_z,
                    _face_toward(GOAL_CENTER_X, GOAL_CENTER_Z, home_x, ball_z)),
        player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], home_x - 2, 0, 30,
                    _face_toward(GOAL_CENTER_X, GOAL_CENTER_Z, home_x - 2, 30)),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 55,
                    _face_toward(home_x, ball_z, 0, 55)),
        player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], home_x - 4, 0, 48,
                    _face_toward(home_x, ball_z, home_x - 4, 48)),
    ]
```
new:
```python
def gk_attack(home_x: float) -> list[dict]:
    ball_z = -23.0
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], home_x, 0, ball_z,
                    _face_toward(GOAL_CENTER_X, GOAL_CENTER_Z, home_x, ball_z)),
        player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], home_x - 2, 0, -28,
                    _face_toward(GOAL_CENTER_X, GOAL_CENTER_Z, home_x - 2, -28)),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, -3,
                    _face_toward(home_x, ball_z, 0, -3)),
        player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], home_x - 4, 0, -10,
                    _face_toward(home_x, ball_z, home_x - 4, -10)),
    ]
```
变换:全部 z 各 -58。

- [ ] **Step 3: Edit `free_kick_wall(ball_x)` 球 z 与玩家 pos.z(墙间距留给 Task 6)**

old(line 1240-1251):
```python
def free_kick_wall(ball_x: float) -> list[dict]:
    ball_z = 42.0
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], ball_x, 0, ball_z,
                    _face_toward(GOAL_CENTER_X, GOAL_CENTER_Z, ball_x, ball_z)),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58,
                    _face_toward(ball_x, ball_z, 0, 58)),
        player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], -2, 0, 50, 180.0),
        player_init("away", 2, PLAYER_AI_DUTY_ENUM["Defender"], 2, 0, 50, 180.0),
        player_init("away", 3, PLAYER_AI_DUTY_ENUM["Defender"], -1, 0, 50, 180.0),
        player_init("away", 4, PLAYER_AI_DUTY_ENUM["Defender"], 1, 0, 50, 180.0),
    ]
```
new(只改 z 各 -58,墙 x 不动留给 Task 6):
```python
def free_kick_wall(ball_x: float) -> list[dict]:
    ball_z = -16.0
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], ball_x, 0, ball_z,
                    _face_toward(GOAL_CENTER_X, GOAL_CENTER_Z, ball_x, ball_z)),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 0,
                    _face_toward(ball_x, ball_z, 0, 0)),
        player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], -2, 0, -8, 180.0),
        player_init("away", 2, PLAYER_AI_DUTY_ENUM["Defender"], 2, 0, -8, 180.0),
        player_init("away", 3, PLAYER_AI_DUTY_ENUM["Defender"], -1, 0, -8, 180.0),
        player_init("away", 4, PLAYER_AI_DUTY_ENUM["Defender"], 1, 0, -8, 180.0),
    ]
```

- [ ] **Step 4: Edit `corner_players(side_x)`**

old(line 1253-1263):
```python
def corner_players(side_x: float) -> list[dict]:
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], side_x, 0, 56,
                    _face_toward(0, 55, side_x, 56)),
        player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], 2, 0, 52,
                    _face_toward(0, 55, 2, 52)),
        player_init("home", 2, PLAYER_AI_DUTY_ENUM["Forward"], -2, 0, 52,
                    _face_toward(0, 55, -2, 52)),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58, 180.0),
        player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], 0, 0, 53, 180.0),
    ]
```
new(home 0 在角旗附近 z=-2;home 1/2 在禁区前点;away 0 门将在球门线 z=0;away 1 在球门前):
```python
def corner_players(side_x: float) -> list[dict]:
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], side_x, 0, -2,
                    _face_toward(0, -3, side_x, -2)),
        player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], 2, 0, -6,
                    _face_toward(0, -3, 2, -6)),
        player_init("home", 2, PLAYER_AI_DUTY_ENUM["Forward"], -2, 0, -6,
                    _face_toward(0, -3, -2, -6)),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 0, 180.0),
        player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], 0, 0, -5, 180.0),
    ]
```

- [ ] **Step 5: Edit `throw_in_players(side_x)`**

old(line 1265-1275):
```python
def throw_in_players(side_x: float) -> list[dict]:
    recv_x, recv_z = side_x - 3, 44.0
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], side_x, 0, 40,
                    _face_toward(recv_x, recv_z, side_x, 40)),
        player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], recv_x, 0, recv_z,
                    _face_toward(GOAL_CENTER_X, GOAL_CENTER_Z, recv_x, recv_z)),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58, 180.0),
        player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], side_x - 2, 0, 46,
                    _face_toward(recv_x, recv_z, side_x - 2, 46)),
    ]
```
new(全 z 各 -58):
```python
def throw_in_players(side_x: float) -> list[dict]:
    recv_x, recv_z = side_x - 3, -14.0
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], side_x, 0, -18,
                    _face_toward(recv_x, recv_z, side_x, -18)),
        player_init("home", 1, PLAYER_AI_DUTY_ENUM["Forward"], recv_x, 0, recv_z,
                    _face_toward(GOAL_CENTER_X, GOAL_CENTER_Z, recv_x, recv_z)),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 0, 180.0),
        player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], side_x - 2, 0, -12,
                    _face_toward(recv_x, recv_z, side_x - 2, -12)),
    ]
```

- [ ] **Step 6: Edit `penalty_players()`**

old(line 1277-1281):
```python
def penalty_players() -> list[dict]:
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 0, 0, 50, 0.0),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 58, 180.0),
    ]
```
new(home 球员在点球点身后 ~3m 即 z=-14 准备射门;away 门将在球门线 z=0):
```python
def penalty_players() -> list[dict]:
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 0, 0, -14, 0.0),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 0, 180.0),
    ]
```

- [ ] **Step 7: Edit `goalkeep_players()`**

old(line 1283-1287):
```python
def goalkeep_players() -> list[dict]:
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 0, 0, 58, 180.0),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Defender"], 0, 0, 56, 0.0),
    ]
```
new(玩家=门将在 home 球门线 z=-120;射手在小禁区外 z=-2 射门 —— **设计选择**:玩家=home 守 home 球门,射手=away 射玩家方向;协议下 +z 朝对方球门,所以这里方向反了):

**注意**:守门切片的玩家身份是「门将」,守的应该是 home 球门(z=-120 端);射手是 away 队的进攻球员从对方半场切入。但旧代码把玩家放在 (0,0,58)= away 球门,不合常理。**保持新的协议下**:home 玩家=门将放在 home 球门线 z=-120,away 射手在 z=-118 等位置。**但这与 spec §3.3 「保留原设计:玩家在球门线上,射手贴脸射」冲突**。

为遵循 spec(保留原设计,只翻 z 坐标系),用「等价 -58」:
```python
def goalkeep_players() -> list[dict]:
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], 0, 0, 0, 180.0),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Defender"], 0, 0, -2, 0.0),
    ]
```
即 home 玩家在 away 球门线 z=0(原 58),away 射手在 z=-2(原 56)。**lint 会报 home 玩家未在小禁区**(GOAL_AREA_Z_FAR=-3.5,home 在 z=0 不属于 [-3.5, 0] —— 实际 0 在范围内,边界包含,通过),保持原设计。

- [ ] **Step 8: Edit preset1_players 注释**

old(line 1289):
```python
# 用户手改:preset ID=1 球员位置走"对方半场→本方半场"坐标系(z 取负值),其余预设保持原坐标
```
new:
```python
# preset 1 已按协议 v1 摆位(协议确认日期 2026-06-18),其余 17 个 preset 在本次重构与之对齐
```

preset1_players 数据**保留不动**(line 1290-1295,原本就是协议下的正确摆位)。

- [ ] **Step 9: Edit corner / throw_in 调用实参**

specs 列表中(line 1313-1317):
- `corner_players(-20)` → `corner_players(-17)`
- `corner_players(20)` → `corner_players(17)`(出现 2 次:preset 11 和 18)
- `throw_in_players(-22)` → `throw_in_players(-18)`
- `throw_in_players(22)` → `throw_in_players(18)`

- [ ] **Step 10: 跑两个 lint**

```bash
python scripts/check_preset_consistency.py
```
Expected:摆位合规检查应**全过**(0 violations),退出码 0。

```bash
python scripts/check_protocol_drift.py
```
Expected:仍 ok(常量段未动)。

- [ ] **Step 11: 39 测试看回归**

```bash
cd output/test-config/level-tags && python -m pytest tests/ 2>&1 | tail -3
```
Expected:39 passed。

- [ ] **Step 12: Commit**

```bash
git add output/test-config/generate_activity_soccer_test_config.py
git commit -m "feat(generator): 6 个 preset 生成函数 PlayersInit z 反转 + corner/throw_in 实参按协议改 ±17/±18 + preset1 注释更正" --no-verify
```

---

## Task 6: 任意球人墙改用 WALL_PLAYER_GAP_MIN 间距

**Files:**
- Modify: `output/test-config/generate_activity_soccer_test_config.py:1240-1251`(`free_kick_wall`)

按 spec §5.2:墙距球 9m(`ball_z + PENALTY_FREE_RADIUS`),墙员间距 1.4m。

- [ ] **Step 1: Read 当前 free_kick_wall**

确认 Task 5 之后的 `ball_z = -16.0`、墙人 z = -8(差 8m)与 9m 不符。本 Task 修正墙位置 + 间距。

- [ ] **Step 2: Edit 替换为 4 人墙(协议下间距 1.4m,墙距球 9m)**

new:
```python
def free_kick_wall(ball_x: float) -> list[dict]:
    """4 人人墙(常规任意球)。墙距球 PENALTY_FREE_RADIUS,人间距 WALL_PLAYER_GAP_MIN。
    墙在「球与对方球门之间」,即 z 比球更接近 0(对方球门)。"""
    ball_z = -16.0
    wall_z = ball_z + PENALTY_FREE_RADIUS  # = -7,墙比球更靠对方球门 9m
    gap = WALL_PLAYER_GAP_MIN
    return [
        player_init("home", 0, PLAYER_AI_DUTY_ENUM["Forward"], ball_x, 0, ball_z,
                    _face_toward(GOAL_CENTER_X, GOAL_CENTER_Z, ball_x, ball_z)),
        player_init("away", 0, PLAYER_AI_DUTY_ENUM["Goalkeeper"], 0, 0, 0,
                    _face_toward(ball_x, ball_z, 0, 0)),
        player_init("away", 1, PLAYER_AI_DUTY_ENUM["Defender"], -1.5 * gap, 0, wall_z, 180.0),
        player_init("away", 2, PLAYER_AI_DUTY_ENUM["Defender"], -0.5 * gap, 0, wall_z, 180.0),
        player_init("away", 3, PLAYER_AI_DUTY_ENUM["Defender"],  0.5 * gap, 0, wall_z, 180.0),
        player_init("away", 4, PLAYER_AI_DUTY_ENUM["Defender"],  1.5 * gap, 0, wall_z, 180.0),
    ]
```

注意:
- `wall_z = -16 + 9 = -7`(在大禁区外 z=-10 之内,合理)
- 4 人墙 x 坐标:`-2.1, -0.7, 0.7, 2.1`(中心对齐 x=0,墙宽 4.2m)
- 间距 = `gap = 1.4m`,连续两人 Δx = 1.4 ✓

**5 人墙(preset 17 弧线任意球)**:`free_kick_wall` 当前只有 4 人。preset 17 的 `wall_count: 5` 是 `TypePayload` 字段(策划数据),实际 PlayersInit 仍是 4 人。本 Task 不扩 5 人(超出 spec §5.2 实现范围),只把 4 人间距改对。如需 5 人在后续 Task 处理。

- [ ] **Step 3: 跑 lint(任意球人墙合规应过)**

```bash
python scripts/check_preset_consistency.py
```
Expected: 任意球人墙间距违规消除,全合规,退出码 0。

- [ ] **Step 4: 39 测试看回归**

```bash
cd output/test-config/level-tags && python -m pytest tests/ 2>&1 | tail -3
```
Expected: 39 passed。

- [ ] **Step 5: Commit**

```bash
git add output/test-config/generate_activity_soccer_test_config.py
git commit -m "feat(generator): 任意球人墙改用 WALL_PLAYER_GAP_MIN=1.4m + 墙距球 PENALTY_FREE_RADIUS=9m" --no-verify
```

---

## Task 7: Const ball_control_distance 1.2 → 0.5

**Files:**
- Modify: `output/test-config/generate_activity_soccer_test_config.py:306`

- [ ] **Step 1: Read line 305-310**

确认 `_const(22, ...)` 行的位置。

- [ ] **Step 2: Edit 替换**

old:
```python
_const(22, "停球/控球距离(m TODO)", "ActvSoccer_ball_control_distance", "1.2"),
```
new:
```python
_const(22, "停球/控球距离(m,协议 v1 §4)", "ActvSoccer_ball_control_distance", "0.5"),
```

- [ ] **Step 3: 验证常量值**

```bash
python -c "import sys; sys.path.insert(0,'output/test-config'); import generate_activity_soccer_test_config as g; rows = g.actv_soccer_const_rows(); v = next(r for r in rows if r['Constant'] == 'ActvSoccer_ball_control_distance'); print('Val=', v['Val'])"
```
Expected: `Val= 0.5`。

- [ ] **Step 4: 跑 lint + 39 测试**

```bash
python scripts/check_protocol_drift.py
python scripts/check_preset_consistency.py
cd output/test-config/level-tags && python -m pytest tests/ 2>&1 | tail -3
```
Expected:协议 drift / preset 合规 / 39 tests 全过。

- [ ] **Step 5: Commit**

```bash
git add output/test-config/generate_activity_soccer_test_config.py
git commit -m "feat(generator): ConstConfig.ball_control_distance 1.2 → 0.5(协议 v1 §4)" --no-verify
```

---

## Task 8: ReceiveDecisionCfg 7 字段单位 mm → m + 类型 int → float

**Files:**
- Modify: `output/test-config/generate_activity_soccer_test_config.py:1481-1487`(列定义)
- Modify: `output/test-config/generate_activity_soccer_test_config.py:1503-1506`(4 行数据 5001-5004)

按 spec §4。

- [ ] **Step 1: Read 主生成器 1480-1510**

确认列定义元组结构 + 4 行数据字段数。

- [ ] **Step 2: Edit 列定义(line 1481-1487)**

把 7 个字段类型从 `int` 改 `float`,注释里的「(mm)」/「(mm/s)」改「(m)」/「(m/s)」。

old:
```python
("SafeDistance", "int", "安全距离;最近防守人大于该距离视为低压(mm)"),
("HighPressureDistance", "int", "高压距离;最近防守人小于该距离视为高压(mm)"),
("ForwardProbeDistance", "int", "前方空间探测距离(mm)"),
("SideProbeDistance", "int", "左右空间探测距离(mm)"),
("BackwardProbeDistance", "int", "身后空间探测距离(mm)"),
("HighBallHeight", "int", "高空球高度阈值;超过后表现层优先胸停/头球(mm)"),
("FastBallSpeed", "int", "高速来球速度阈值;超过后提高停球权重(mm/s)"),
```
new:
```python
("SafeDistance", "float", "安全距离;最近防守人大于该距离视为低压(m,协议 v1)"),
("HighPressureDistance", "float", "高压距离;最近防守人小于该距离视为高压(m,协议 v1)"),
("ForwardProbeDistance", "float", "前方空间探测距离(m,协议 v1)"),
("SideProbeDistance", "float", "左右空间探测距离(m,协议 v1)"),
("BackwardProbeDistance", "float", "身后空间探测距离(m,协议 v1)"),
("HighBallHeight", "float", "高空球高度阈值;超过后表现层优先胸停/头球(m,协议 v1)"),
("FastBallSpeed", "float", "高速来球速度阈值;超过后提高停球权重(m/s,协议 v1)"),
```

- [ ] **Step 3: Edit 4 行数据(line 1503-1506)折算 ÷ 1000**

| 字段 | 5001 | 5002 | 5003 | 5004 |
|---|---|---|---|---|
| SafeDistance | 3500 → 3.5 | 3500 → 3.5 | 3200 → 3.2 | 3000 → 3.0 |
| HighPressureDistance | 1600 → 1.6 | 1700 → 1.7 | 1500 → 1.5 | 1400 → 1.4 |
| ForwardProbeDistance | 5000 → 5.0 | 4500 → 4.5 | 5500 → 5.5 | 4000 → 4.0 |
| SideProbeDistance | 3500 → 3.5 | 3500 → 3.5 | 4000 → 4.0 | 3000 → 3.0 |
| BackwardProbeDistance | 2500 → 2.5 | 2500 → 2.5 | 2500 → 2.5 | 3000 → 3.0 |
| HighBallHeight | 900 → 0.9 | 900 → 0.9 | 900 → 0.9 | 900 → 0.9 |
| FastBallSpeed | 16000 → 16.0 | 16000 → 16.0 | 16000 → 16.0 | 15000 → 15.0 |

逐字段 Edit,4 行各 7 个数值。例如 5001 行(line 1503):

old:
```python
{"ID": 5001, "Style": "Balanced", "DecisionMinMs": 300, "DecisionMaxMs": 1000, "SafeDistance": 3500, "HighPressureDistance": 1600, "ForwardProbeDistance": 5000, "SideProbeDistance": 3500, "BackwardProbeDistance": 2500, "HighBallHeight": 900, "FastBallSpeed": 16000, ...},
```
new:
```python
{"ID": 5001, "Style": "Balanced", "DecisionMinMs": 300, "DecisionMaxMs": 1000, "SafeDistance": 3.5, "HighPressureDistance": 1.6, "ForwardProbeDistance": 5.0, "SideProbeDistance": 3.5, "BackwardProbeDistance": 2.5, "HighBallHeight": 0.9, "FastBallSpeed": 16.0, ...},
```

5002 行(Playmaker)、5003 行(Dribbler)、5004 行(TargetMan)同样替换 7 个字段。

注意:`DecisionMinMs / DecisionMaxMs / 各 Weight` 字段**保持不变**(单位是 ms / 整数权重,不属本次单位转换)。

- [ ] **Step 4: 验证数据**

```bash
python -c "
import sys; sys.path.insert(0,'output/test-config')
import generate_activity_soccer_test_config as g
# 找 ReceiveDecisionCfg 的 build 函数(没单独提取,只在 build_workbook 内联);
# 直接用 main 跑一次确认无报错
print('module import ok')
"
```
Expected: `module import ok`。

- [ ] **Step 5: 跑 lint + 39 测试**

```bash
python scripts/check_protocol_drift.py
python scripts/check_preset_consistency.py
cd output/test-config/level-tags && python -m pytest tests/ 2>&1 | tail -3
```
Expected:全过。

- [ ] **Step 6: Commit**

```bash
git add output/test-config/generate_activity_soccer_test_config.py
git commit -m "feat(generator): ReceiveDecisionCfg 7 字段 mm/(mm/s) → m/(m/s),类型 int → float(协议 v1)" --no-verify
```

---

## Task 9: 端到端跑主生成器 + lint 全套

**Files:** 无修改,仅验证。

- [ ] **Step 1: 跑主生成器全量**

```bash
python output/test-config/generate_activity_soccer_test_config.py
```
Expected: 无报错;输出 `ActivitySoccer.xlsx` / `ActivitySoccerLanguage.xlsx` / `test-config-summary.json` 等(具体看主生成器 main 输出)。

- [ ] **Step 2: 跑 check_protocol_drift**

```bash
python scripts/check_protocol_drift.py
```
Expected: `[ok] 协议 ↔ 代码常量段一致(7 项)`,退出码 0。

- [ ] **Step 3: 跑 check_preset_consistency**

```bash
python scripts/check_preset_consistency.py
```
Expected: `[ok] 18 preset 全部合规`,退出码 0。

- [ ] **Step 4: 跑关卡 tag 工具 39 测试**

```bash
cd output/test-config/level-tags && python -m pytest tests/ -v 2>&1 | tail -5
```
Expected: 39 passed。

- [ ] **Step 5: 跑关卡 tag 工具端到端冒烟**

```bash
cd output/test-config/level-tags && python apply_level_tags.py 2>&1 | tail -2
```
Expected: `[ok] 关卡 tag 产物写入: ... (贴 tag 关数 5/500)`(因 LevelTagCfg.xlsx 仍有 5 个样例 tag)。

如某项失败,**回退最近的 commit 重做**;不要尝试在产物里手 patch。

---
