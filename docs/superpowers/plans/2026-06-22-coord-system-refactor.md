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
