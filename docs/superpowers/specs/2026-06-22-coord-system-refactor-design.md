# 2026 世界杯活动 · 坐标系协议 v1 派生重构 设计文档

**日期**: 2026-06-22
**状态**: 已批准设计,待写实现计划
**Spec 来源**:`references/soccer-coordinate-protocol.md` v1 §12 派生改动清单(P0×7 / P1×3 / P2×1)
**前置**:协议 v1 主体已确认(commit `ea1af97`),18 项 TBD 全部填回。

---

## 1. 目标 + 改动范围

### 1.1 目标

把主生成器(`generate_activity_soccer_test_config.py`)按协议 v1 重写,实现「文件常量 ↔ 协议 v1 完全一致」+ 落 2 条 lint(协议 drift / preset 合规)+ 状态机推进协议到 **v1.1**。

### 1.2 包含

- 1 Python 文件:`output/test-config/generate_activity_soccer_test_config.py`
  - 顶部新增协议 v1 常量段(~50 行)
  - 18 个 preset 的 BallPos / TargetPoint / pos.z 重写到协议坐标系
  - `_free_kick_wall` 改用 `WALL_PLAYER_GAP_MIN` 间距
  - Const 表 `ball_control_distance = 1.2 → 0.5`
  - `ReceiveDecisionCfg` 7 字段 mm/(mm/s) → m/(m/s)(类型 int → float)
  - 删 `:774-778` WARN 注释段(常量已对齐协议后失效)
- 1 Markdown:`references/soccer-coordinate-protocol.md`
  - 协议状态从 v1 主体 → v1.1 派生改动已落地
  - §12 表头加状态机说明 + 每条改动加 `状态` 列
- 2 新脚本:`scripts/check_protocol_drift.py` + `scripts/check_preset_consistency.py`

### 1.3 不包含

- 关卡 tag 工具(`output/test-config/level-tags/`)及 39 测试不动。重构后 **39 测试必须 passing 0 回归**。
- 旧版 `generate_worldcup_test_config.py` 不动(不属本协议覆盖范围)。
- §12 #11(`level_tag_lib.PatchContext.library` 加 `protocol_v1` 子键)归 P2,不在本次。
- TBD-18(控球距离起算锚点)等程序方,不在本次。

---

## 2. 架构 — 常量层

### 2.1 常量段(文件顶部,imports 后)

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
```

### 2.2 helper 函数(常量段后)

```python
def away_goal_target(y: float = 0.0) -> str:
    """对方球门 + 指定 y(高度)的 TargetPoint JSON。"""
    return json.dumps({"x": 0.0, "y": y, "z": AWAY_GOAL_CENTER[2]})

def penalty_ball_pos() -> str:
    """点球 BallPos JSON。"""
    return json.dumps({"x": PENALTY_SPOT[0], "y": 0.0, "z": PENALTY_SPOT[2]})

def corner_ball_pos(side: str) -> str:
    """角球 BallPos JSON,side='left'/'right'。"""
    pos = CORNER_LEFT_BALL if side == "left" else CORNER_RIGHT_BALL
    return json.dumps({"x": pos[0], "y": 0.0, "z": pos[2]})
```

---

## 3. 18 个 preset 重写映射

### 3.1 BallPos 对照(全量)

| Preset | 类型 | old (x, z) | new (x, z) | 新值来源 |
|---|---|---|---|---|
| 1 右路单刀 | attack | (12, 35) | (12, -23) | 等价 -58 |
| 5 左路单刀 | attack | (-12, 35) | (-12, -23) | 同上 |
| 6 中路突破 | attack | (0, 36) | (0, -22) | 同上 |
| 16 中路吊射 | attack | (0, 30) | (0, -28) | 同上 |
| 2 中路任意球 | free_kick | (0, 42) | (0, -16) | 同上 |
| 7 左侧任意球 | free_kick | (-10, 44) | (-10, -14) | 同上 |
| 8 右侧任意球 | free_kick | (10, 44) | (10, -14) | 同上 |
| 17 弧线任意球 | free_kick | (4, 40) | (4, -18) | 同上 |
| 3 标准点球 | penalty | (0, 50) | (0, -11) | **协议 §3.4 PENALTY_SPOT** |
| 9 加压点球 | penalty | (0, 50) | (0, -11) | **协议 §3.4 PENALTY_SPOT** |
| 10 左角球 | corner | (-20, 58) | (-17, -1) | **协议 §3.5 CORNER_LEFT_BALL** |
| 11 右角球 | corner | (20, 58) | (17, -1) | **协议 §3.5 CORNER_RIGHT_BALL** |
| 18 后点包抄 | corner | (20, 58) | (17, -1) | **协议 §3.5 CORNER_RIGHT_BALL** |
| 12 左界外球 | throw_in | (-22, 40) | (-18, -18) | x = -FIELD_X_HALF |
| 13 右界外球 | throw_in | (22, 40) | (18, -18) | x = FIELD_X_HALF |
| 4 基础守门 | goalkeep | (0, 56) | (0, -2) | 在小禁区 GOAL_AREA_Z_FAR=-3.5 内 |
| 14 大范围守门 | goalkeep | (0, 56) | (0, -2) | 同上 |
| 15 近距扑点 | goalkeep | (0, 54) | (0, -4) | 在大禁区内 |

### 3.2 TargetPoint 重写

所有 TargetPoint 中 `z=58` → `z=0`(对方球门线)。具体:
- preset 1, 5, 6, 16(attack):TargetPoint z=58 → 0,y 保留(吊射 1.5)
- preset 2, 7, 8, 17(free_kick):TargetPoint z=58 → 0,y 保留(1.8 / 2.0)
- preset 3, 9(penalty):TargetPoint z=58 → 0,y=0.5 保留
- preset 10, 11, 18(corner):TargetPoint z=55 → -3,z=54 → -4(后点包抄,z 偏向远点)
- preset 12, 13(throw_in):TargetPoint z=44 → -14(等价 -58)
- preset 4, 14, 15(goalkeep):TargetPoint = None,不动
- 全局默认 `'{"x":0,"y":0,"z":58}'`(line 1414)→ `'{"x":0,"y":0,"z":0}'`

### 3.3 PlayersInit 重写

每个 preset 生成函数(`gk_attack`, `free_kick_wall`, `corner_players`, `throw_in_players`, `penalty_players`, `goalkeep_players`)内 `pos.z` 全部 `- 58`,`facing` 不变。

特殊处理:
- `penalty_players`:home (0,0,50) → (0,0,-8),away (0,0,58) → (0,0,0)。注意 home 球员**不在点球点本身**,在点球点身后 3m 准备射门,合理。
- `goalkeep_players`:home (0,0,58) → (0,0,0)(玩家=门将,在球门线上),away (0,0,56) → (0,0,-2)(射手,贴脸射,虽然非常规但保留原设计)。
- `corner_players`:home/away 全员 z 各 -58,但 BallPos 已变为 (±17, 0, -1),需检查 `corner_players(side_x)` 函数中 side_x 实参也要从 ±20 改 ±17(代码 line 1313-1315 的实参)。

`PLAYER_INIT_DEFAULT`(line 776):`{"x":0,"y":0,"z":0,"facing":0}` 已经在 z=0,**不需要改**(原本就是默认空,不指代任何场地位置)。

### 3.4 _build_levels 调用 corner

`_build_presets` 调用 `corner_players(-20)` 和 `corner_players(20)`(line 1313-1315),**实参也要改成 -17 / 17**,匹配新协议。

`throw_in_players(-22)` → `throw_in_players(-18)`,`throw_in_players(22)` → `throw_in_players(18)`(协议边线 ±18)。

### 3.5 preset 1 先验

代码 line 1289-1295 的 `preset1_players` 已经是负 z 坐标(`z=-23/-30/-5/-12`),但**注释「用户手改:对方半场→本方半场」误导**。这组数据在协议 v1 下是正确的(对方半场 = z 接近 0,本方半场 = z 接近 -120)。改动:
- 注释改为 `# preset 1 已按协议 v1 摆位,其余 17 个 preset 在本次重构与之对齐`
- 数据保留不动

---

## 4. ReceiveDecisionCfg 单位转换

### 4.1 字段类型 + 值

7 字段从 `int` (mm) 改 `float` (m),数值 ÷ 1000:

| 字段 | 5001 | 5002 | 5003 | 5004 |
|---|---|---|---|---|
| SafeDistance | 3.5 | 3.5 | 3.2 | 3.0 |
| HighPressureDistance | 1.6 | 1.7 | 1.5 | 1.4 |
| ForwardProbeDistance | 5.0 | 4.5 | 5.5 | 4.0 |
| SideProbeDistance | 3.5 | 3.5 | 4.0 | 3.0 |
| BackwardProbeDistance | 2.5 | 2.5 | 2.5 | 3.0 |
| HighBallHeight | 0.9 | 0.9 | 0.9 | 0.9 |
| FastBallSpeed | 16.0 | 16.0 | 16.0 | 15.0 |

### 4.2 schema 改注释

`make_sheet` 列定义 line 1481-1487:
- `("SafeDistance", "int", "...(mm)")` → `("SafeDistance", "float", "...(m,协议 v1)")`
- 对应 6 个其他字段同改
- 列类型 `int` → `float`

---

## 5. Const 改动 + 任意球人墙

### 5.1 ball_control_distance

代码 line 306:
```python
_const(22, "停球/控球距离(m TODO)", "ActvSoccer_ball_control_distance", "1.2"),
```
改:
```python
_const(22, "停球/控球距离(m,协议 v1 §4)", "ActvSoccer_ball_control_distance", "0.5"),
```

### 5.2 任意球人墙间距

代码 line 1240-1251 `free_kick_wall(ball_x)`:

old(4 人,间距 1.0):
```python
player_init("away", 1, ..., -2, 0, 50, 180.0),
player_init("away", 2, ..., 2, 0, 50, 180.0),
player_init("away", 3, ..., -1, 0, 50, 180.0),
player_init("away", 4, ..., 1, 0, 50, 180.0),
```

new(4 人,间距 1.4,中心对球):
```python
gap = WALL_PLAYER_GAP_MIN
player_init("away", 1, ..., -1.5*gap, 0, ball_z + 8, 180.0),
player_init("away", 2, ..., -0.5*gap, 0, ball_z + 8, 180.0),
player_init("away", 3, ...,  0.5*gap, 0, ball_z + 8, 180.0),
player_init("away", 4, ...,  1.5*gap, 0, ball_z + 8, 180.0),
```

注意:墙距球 ≥ 9m(协议 §5),所以墙的 z = ball_z + 8(在协议下,+z 朝对方球门,因 ball_z 是负值,+8 = 离球门更近 8m,但还应 ≥ 9m;此处 8 是最低折中,需在 lint 中自适配)。

更稳妥:墙位置 `ball_z + PENALTY_FREE_RADIUS`(取 9m,贴线但不违规)。

5 人墙(preset 17 弧线任意球):x = -2.0\*gap, -1.0\*gap, 0, 1.0\*gap, 2.0\*gap(间距 1.4)。

具体公式由 plan 阶段精化,本 spec 锁定**间距下限 = WALL_PLAYER_GAP_MIN**。

---

## 6. 验证(三道 lint + 39 测试)

### 6.1 `scripts/check_preset_consistency.py`

```python
# 加载主生成器 _build_presets,对每个 preset 断言:
# 1. BallPos.z ∈ [FIELD_Z_FAR, FIELD_Z_NEAR]
# 2. BallPos.x ∈ [-FIELD_X_HALF, FIELD_X_HALF]
# 3. BallPos.y ∈ [0, GOAL_HEIGHT]
# 4. PlayersInit 内 pos.z 同范围
# 5. 点球 preset(3, 9):BallPos == PENALTY_SPOT(忽略 y)
# 6. 角球 preset(10, 11, 18):
#      BallPos in {CORNER_LEFT_BALL, CORNER_RIGHT_BALL}
# 7. 守门 preset(4, 14, 15):
#      home 玩家 pos.z ∈ [GOAL_AREA_Z_FAR, FIELD_Z_NEAR]
# 8. 任意球 preset(2, 7, 8, 17):
#      away 防守墙连续两人 |Δx| ≥ WALL_PLAYER_GAP_MIN - 0.001
# 退出码 0 = 全合规;1 = 有违规(列出违规清单)。
```

### 6.2 `scripts/check_protocol_drift.py`

```python
# 解析 references/soccer-coordinate-protocol.md §3-§4 的所有 markdown
# 表格行(模式 `| 字段 | 值 | 单位 |`),与主生成器顶部常量段
# (从 `# === 坐标系协议 v1 ===` 到下一个 `# ===` 之间的 Python 名 = 字面量)对照。
#
# 协议字段名 → 代码常量名 映射(硬编码,小):
#   球门宽度 ↔ GOAL_WIDTH
#   球门高度 ↔ GOAL_HEIGHT
#   死角厚度 ↔ DEAD_CORNER_THICKNESS
#   大禁区 z 边界 ↔ PENALTY_AREA_Z_FAR
#   ... (~15 项)
#
# 不一致即非零退出。
```

### 6.3 关卡 tag 工具 39 测试

`pytest output/test-config/level-tags/tests/`,期望 39 passed。重构期间这是回归网。

### 6.4 验证顺序

plan 第一个 task 先落空 lint 框架(只校核心几条断言,跑当前代码会 fail),第二个 task 修 GOAL_CENTER_Z + 常量段(此时 6.2 lint 应过,6.1 仍 fail),后续 task 逐步迁数据让 6.1 lint 也过。最终所有重构完成 = 三道 lint + 39 测试全过。

---

## 7. 协议升级到 v1.1 + 状态机

### 7.1 协议 §12 加状态机表头

在 §12 派生改动清单标题下、表格前,加一段:

```markdown
### 状态机

- **v1**:主体确认,18 项 TBD 全填。代码侧未跟进,产物空间字段不可信。
- **v1.1**:P0 全部完成 + 三道 lint 全过 + 关卡 tag 39 测试无回归。代码 ↔ 协议主体一致,产物可在游戏内落地。
- **v2**:P1 全部完成(常量段 self-documenting + lint 工具落定)。

每条改动 commit 后责任人在表「状态」列勾 ✅。勾完所有 P0 + lint 三道全过,**才允许把头部状态从 v1 改 v1.1**。
```

### 7.2 §12 表加状态列

每行加一列「状态」(✅ / ☐),本次重构 7 条 P0 + 1 条 P1(#10 lint)勾 ✅,#9 / #11 仍 ☐。

### 7.3 协议头部状态升级

```markdown
> **状态**:**v1.1 派生改动已落地**(2026-06-22 完成)。代码与协议主体一致,产物可在游戏内落地。
```

### 7.4 删主生成器 WARN 注释

`generate_activity_soccer_test_config.py:774-778` 的 `WARN(2026-06-18)` 注释段在常量对齐后失效,删除。

### 7.5 list_tbd 刷新 + commit

跑 `python scripts/list_tbd.py` 看协议状态计数,提交所有改动。

---

## 8. 回滚策略

若重构中发现协议某项数值不对(如 preset 数据落地后程序方 playtest 发现球门高 3m 不对),**不要**直接改主生成器常量。流程:
1. 在协议 §X 改值 + 加修订日期。
2. 重跑 `check_protocol_drift.py`,代码侧报 drift。
3. 再修主生成器常量,跑全套 lint 通过。
4. 再升协议状态(v1.1.1 / v1.2 视情况)。

这保证「协议 = 真相」的单源约束在任何时候都成立。

---

## 9. 实现顺序约束

按依赖顺序执行(plan 任务化时按此排):

1. **Lint 框架**(空壳实现,跑当前代码 fail) — 提供回归网
2. **常量段 + helper** — 主生成器顶部
3. **GOAL_CENTER_Z = 58 → 0**(等价于 `AWAY_GOAL_CENTER[2]`)— 触发后续 preset 重写
4. **18 个 preset BallPos 重写**
5. **18 个 preset TargetPoint 重写 + 全局默认**
6. **PlayersInit z 偏移 + corner/throw_in 实参改**
7. **_free_kick_wall 用 WALL_PLAYER_GAP_MIN**
8. **Const ball_control_distance**
9. **ReceiveDecisionCfg 单位转**
10. **lint 实施**(把 6.1/6.2 的断言写完整,跑过)
11. **协议升级到 v1.1 + 状态机 + 删 WARN**

每步 commit 一次,中间 push,失败回滚便宜。

---

## 10. 验收清单

- ✅ `scripts/check_preset_consistency.py` 跑过(0 violations)
- ✅ `scripts/check_protocol_drift.py` 跑过(0 drift)
- ✅ `pytest output/test-config/level-tags/tests/` 39 passed
- ✅ `python output/test-config/generate_activity_soccer_test_config.py` 不报错跑通
- ✅ 协议头部状态 = v1.1
- ✅ §12 P0 7 条全部 ✅,#10 ✅
- ✅ 主生成器 `:774` 起的 WARN 注释段已删
- ✅ `python scripts/list_tbd.py`:`soccer-coordinate-protocol.md` 编号 TBD = 0
- ✅ 全部 commits push 到 origin/main
