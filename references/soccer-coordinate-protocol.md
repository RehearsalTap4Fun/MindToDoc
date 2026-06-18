# 足球场地坐标系协议 · 草稿

> **状态**:**草稿,多处 TBD 等程序方/美术方确认**。共 **19 个编号 TBD**(`scripts/list_tbd.py` 实测,2026-06-18)。
> **来源**:从 `output/test-config/generate_activity_soccer_test_config.py` 中 18 个 preset 的实际坐标反推,补充 FIFA 标准场地与切片规则约束。
> **用途**:新增切片预设 / 切片实例 / patch 函数 涉及空间数据时,所有人(策划 / 程序 / AI Agent / 关卡 tag 工具)以本协议为准。
>
> **维护约定**:
> - 数值变更必须同步更新 `generate_activity_soccer_test_config.py:775` 的常量段。
> - TBD 项必须由程序方或美术方填写,**未填写前禁止生成任何新切片预设**。
> - 本协议与 `2026世界杯主题活动-开发文档.md` §3.2(切片摆位/物理参数)交叉参考;若冲突,以主案为准并同步本协议。
> - 跑 `python scripts/list_tbd.py` 查所有 references/*.md 的 TBD 当前状态;协议每填完 N 项后建议重跑刷新本头部计数。

---

## 0. 现状已知不一致(必须先解决)

`generate_activity_soccer_test_config.py:1289-1295` 的 **preset 1(右路单刀)** 使用了 **负 z 坐标**(`z=-23/-30/-5/-12`),且球员朝向(facing)使用负角度(-27.6 / -19.7),与其余 17 个 preset 使用正 z 坐标(`z=30..58`)+ 正/180 朝向**坐标系不一致**。

代码注释写「对方半场→本方半场」,暗示 preset 1 用了**反向坐标系**。可能成因:测试期手改、未与生成器其它代码对齐。

**TBD-0**:程序运行时按 preset 1 的负 z 还是其余 17 个的正 z 演算?哪一组是「真相」?
**TBD-0a**:确定后,补一个 lint 跑现有 18 个 preset 检查 z 取值同号(异号即报错)。

---

## 1. 坐标系基础

### 1.1 单位

**TBD-1**:坐标系单位 = ?(候选:m / cm / mm / 自定义网格)

| 字段 | 当前值 | 可能单位 |
|---|---|---|
| `BallPos.z` | 30..58(正向 preset)/ -23..-30(preset 1) | m(若按 FIFA 半场 ≈52.5m,58 接近) |
| `pos.x` | -22..22 | m(若按 FIFA 半宽 ≈34m,22 在合理范围) |
| `pos.y` | 一律 0(地面) | m |
| `BallPos.y` | 0..2.0 | m(吊射目标 1.8/弧线 2.0 像高度米) |
| `ConstConfig.ball_control_distance` | 1.2 | m(标 TODO,待确认) |
| `ConstConfig.move_speed_run_min/max` | 4 / 8 | m/s |
| `ReceiveDecisionCfg.HighBallHeight` | 900 | **mm**(注释明确)— 与 BallPos.y 的 m 不一致! |
| `ReceiveDecisionCfg.SafeDistance` | 3500 | **mm**(注释明确) |
| `ReceiveDecisionCfg.FastBallSpeed` | 16000 | **mm/s** |

**已发现**:`ReceiveDecisionCfg` 系列字段单位 = mm/mm/s,与 `BallPos / pos / ball_control_distance` 的 m 不一致。**两套单位混用**。

**TBD-1a**:这是有意的(决策模块用整数 mm,演算用浮点 m)还是 bug?若有意,在每个使用单位的常量旁边强制标 `_mm` 后缀,反之统一为 m。

### 1.2 轴向

从代码反推:
- **x**:左右(横向),正方向 = 进攻方右侧
- **y**:高度(垂直),0 = 地面
- **z**:纵深,**正方向 = home 进攻方向(对方球门)**(TBD-2 待确认)

**TBD-2**:home(玩家)进攻方向是 +z 还是 -z?preset 1 用负 z 暗示「-z 是对方半场」,与其余 17 个 preset 矛盾。

### 1.3 手系

**TBD-3**:左手系还是右手系?(影响 yaw 角符号 / AI 镜像逻辑)
- 现有 `_yaw_deg(dx, dz) = atan2(dx, dz)` —— 在右手系里这是「以 +z 为 0°,顺时针为正」,与 Unity 默认一致。但需程序方确认引擎选型。

### 1.4 原点位置

**TBD-4**:原点 (0,0,0) 位于场地哪一点?
候选:
- **A 中圈**(常规)— 此时 home 球门 z=-52.5,away 球门 z=+52.5
- **B 我方球门线中心**— 此时 +z 方向是对方球门,away 球门 z=105
- **C 我方半场底端**— 当前 GOAL_CENTER_Z=58 / 对方球门附近,暗示原点偏近本方半场端

从 `GOAL_CENTER_Z=58` 反推,**当前默认 = C 类**,场地全长大约 116m(若 z 是 m),本方球门 z ≈ -58 / 中线 z=0 / 对方球门 z=58。

需程序方确认。

### 1.5 facing 角度

`_yaw_deg(dx, dz) = round(degrees(atan2(dx, dz)), 1)`:
- 0° = 朝 +z
- 90° = 朝 +x
- 180° = 朝 -z
- -90° / 270° = 朝 -x

**所有 facing 字段统一用 [-180, 180] 还是 [0, 360]?**

当前数据混用:`away.Goalkeeper.facing=180.0`(正向 preset)、`preset1.away.0.facing=180.0` 一致;但 `preset1.home.0.facing=-27.6` 用了负值。

**TBD-5**:facing 范围统一为 [-180, 180]、[0, 360]、还是不限?程序解析端如何处理 wrap-around。

---

## 2. 场地几何边界

按推断,FIFA 标准场地按 1:1 比例换算到本坐标系(若单位 = m,原点 = 我方半场底端):

```
                 +z (对方球门方向)
                  ↑
                  │
   ┌──────────────┼──────────────┐  away 球门线 (z = +58, TBD)
   │              │              │
   │    away 半场  │              │
   │              │              │
   │              │              │
   ├──────────────┼──────────────┤  中线 (z = 0?)
   │              │              │
   │    home 半场  │              │
   │              │              │
   │              │              │
   └──────────────┼──────────────┘  home 球门线 (z = -58, TBD)
                  │
                  │
   -x  ←──────────┼──────────→  +x
                  │
                  │
                 -z
```

| 区域 | 边界(TBD,等程序方) |
|---|---|
| 整场 x 范围 | x ∈ [-34, 34](FIFA 68m 宽,半宽 34m;preset 用 -22..22 在合理范围内) |
| 整场 z 范围 | z ∈ [-52.5, 52.5](若中线为 0)/ z ∈ [0, 105](若我方球门为 0)/ **当前实测 z=58 暗示 [-58, 58] 系**,需确认 |
| 球门线(home / away) | z = -58 / +58(当前 GOAL_CENTER_Z=58) |
| 中线 | z = 0(若双侧对称)— **TBD-6** |
| 边线 | x = ±34(FIFA 标准 68m 宽)— **TBD-7** |

**TBD-6 / TBD-7**:确认整场 x/z 范围;preset 12/13(界外球)用 `x=±22`,这是「边线」吗?若是,场地仅 44m 宽(远小于 FIFA 68m),不合常理。可能 preset 数值是缩比示意。

---

## 3. 关键功能区

### 3.1 球门(goal)

| 字段 | 当前值 | 单位 | 备注 |
|---|---|---|---|
| 球门中心 (away) | `(0, 0, 58)` | m? | 代码常量 `GOAL_CENTER_X / GOAL_CENTER_Z` |
| 球门中心 (home) | **TBD**(应为 `(0, 0, -58)` 镜像,但未在代码中定义) | m? | 当前不需要(玩家恒为 home),但 AI 全场跑位需要 |
| 球门宽度(立柱间距) | **TBD**(FIFA = 7.32m,候选 7.32 或缩比值) | m? | 守门切片划线判定边界依赖此 |
| 球门高度(横梁高) | **TBD**(FIFA = 2.44m;preset 16 吊射 BallPos.y=1.5,17 弧线 y=2.0,18 后点包抄 y=2.0,合理) | m? | TargetPoint.y 上限 |
| 死角定义 | `dead_corner_can_save = 0`(横梁 + 立柱内 ?cm 不可扑) | **TBD** | spec §3.2 / Const 表 |

### 3.2 大禁区(penalty area)

| 字段 | 当前值 | 单位 |
|---|---|---|
| 大禁区 z 边界 | **TBD**(FIFA 距球门线 16.5m,候选 z = 58-16.5 = 41.5 / 或缩比值) | m? |
| 大禁区 x 边界 | **TBD**(FIFA 立柱外侧扩 16.5m,候选 x = ±20.16) | m? |

实际 preset 内含的禁区相关:
- preset 9(加压点球)球员 home `pos=(0,0,50)`(超出推断的禁区线 z=41.5)— **检查 TBD**
- preset 4 / 14 / 15(守门)球员 away.Defender `pos=(0,0,56)` 在大禁区内(若禁区 z>=41.5)
- preset 2 / 7 / 8(任意球人墙)away.Defender `pos.z=50` 在禁区外

### 3.3 小禁区(goal area)

**TBD**:小禁区(FIFA 距球门线 5.5m / 候选 z=58-5.5=52.5)用于守门切片站位约束?或仅美术参考?

### 3.4 点球点

`preset 3 / 9` 把球放在 `(0, 0, 50)`(距球门 8m)。**FIFA 标准是距球门线 11m / 即 z=47**。

**TBD-8**:本游戏点球点 z = 50 还是 47?是否需要修正现有 preset 3/9?
**TBD-8a**:点球开球时,弧线外其他球员距球 9.15m → 在本坐标系内是 `circle((0,0,50), 9.15)` 外。当前 preset 3/9 都只放门将+前锋 2 人,无其他防守球员,**回避了规则**。如果未来 tag 增加防守球员,需要工具自动判断弧外站位。

### 3.5 角球点

`preset 10/11/18` 用 `BallPos = (±20, 0, 58)`,即角旗位置。

**TBD-9**:角旗 x 应该 = ±34(场地半宽)还是 ±20(本场地缩比)?当前 ±20 暗示场地半宽 = 20。

### 3.6 中圈

**TBD-10**:中圈半径(FIFA = 9.15m);开球切片是否使用?当前 18 个 preset **没有**对应「kick_off / 中圈开球」类型,先标 TBD。

---

## 4. 球员/物体物理参数

| 参数 | 来源 | 当前值 | 单位 | 备注 |
|---|---|---|---|---|
| 球员碰撞半径 | **TBD** | — | — | 决定摆位间距下限;preset 2 人墙间距 x=1(`-1,1,-2,2`)若球员半径>0.5 重叠 |
| 球碰撞半径 | **TBD** | — | — | |
| 球员可控球距离 | `ConstConfig.ball_control_distance` | 1.2 | m(标 TODO) | |
| 默认行走速度 | `ConstConfig.move_speed_walk` | 2.5 | m/s(标 TODO) | |
| 跑速下限 | `ConstConfig.move_speed_run_min` | 4 | m/s | |
| 跑速上限 | `ConstConfig.move_speed_run_max` | 8 | m/s | |
| 各倍率 | `ConstConfig.move_speed_ratio_*` | jog=0.75 / sprint=1.25 / dribble=0.85 / press=1.1 / keeper_lateral=0.9 | 相对 run | |
| 出球力下限 | `ConstConfig.kick_force_min` | 10 | **TBD**(N? m/s²?) | |
| 出球力上限 | `ConstConfig.kick_force_max` | 25 | **TBD** | |

---

## 5. 切片类型 → 法定摆位约束

每种 SliceType 有 FIFA 规则约束,工具生成新预设/实例时**应当机器校验**:

| SliceType | 约束 | 当前 preset 是否合规 |
|---|---|---|
| 1 attack | 进攻方至少 1 球员在 BallOwner 位;BallOwner ∈ home;无越位检查(本游戏可能不做) | 1/5/6/16 OK |
| 2 free_kick | 防守方人墙 ≥ 9.15m 距球;BallOwner ∈ home;球落点不可越位 | preset 2/7/8/17:墙 z=50,球 z=42-44,距离 6-8 → **不足 9.15m,违反 FIFA**(本游戏可能放宽) |
| 3 penalty | 球必须在点球点;门将必须在球门线;其他球员在禁区+弧外距球 9.15m | preset 3/9 OK(简化为 2 人) |
| 4 corner | 球必须在角旗 1m 半径内;防守方距球 ≥ 9.15m | preset 10/11/18 球距 home=`(±20,58)→home(side_x,56)` 即 2-4m 不足 9.15m → **同上** |
| 5 throw_in | 球员双脚必须在边线后(场地外);头顶双手投掷 | preset 12/13:发球者 x=±22,边线 x=?,需先确认边线在哪 |
| 6 goalkeep | 玩家=门将,必须在小禁区内;射手必须在球门远端 | preset 4/14/15:玩家(home.0)在 (0,0,58)= 球门线上,射手(away.0)在 (0,0,56)= 紧邻球门;**这是非常规守门切片摆位**(射手贴脸射) |

**TBD-11**:本游戏放宽到什么程度?若工具未来生成预设,这些约束应当**软警告**(不影响产物)还是**硬错误**(拒绝生成)?

---

## 6. 镜头与视角

| 字段 | 来源 | 当前用法 |
|---|---|---|
| `CameraFov` | preset 字段 | 40-52 度;一般 1 倍体素 = 度 |
| `SliceFlowCfg.CamYawRange` | flow 字段 | TBD,主案 §3.2 提及但当前未填 |
| `SliceFlowCfg.CamYawDefault` | flow 字段 | TBD |
| `TargetPoint` | preset 字段 | `(x,y,z)` 球门中心 / 远点 / 近点 |

**TBD-12**:CameraFov 的「合理区间」(40-52 是手调还是有公式?守门切片为何用 50,任意球用 41-42?)

---

## 7. AI 行为半径

依赖坐标系的 modifier 参数:

| Modifier | 参数 | 当前值 | 单位 | 备注 |
|---|---|---|---|---|
| 4001 moving_keeper | speed=1.0, range=2.5 | 1.0/2.5 | TBD/m? | range 是「距门将原始位置的横向半径」?半径 2.5 在 7.32m 球门里是 ⅓ 球门宽,合理 |
| 4002 moving_keeper(困难) | speed=1.5, range=3.5 | 同上 | | |
| 4005 moving_keeper(极限) | speed=2.0, range=4.5 | | | range=4.5 已超出半球门宽(3.66)<br>**这意味着门将能跑到立柱外?** TBD |
| 4006 narrow_angle | shrink=0.7 | 0.7 | 倍数 | 主案 §3.2:**OperableAngle × 0.7**(乘法)而非 -0.7(减法),需明确 |
| 4007 random_dive | randomness=0.6 | 0.6 | [0,1] 概率 | |

**TBD-13**:逐个 modifier 写明「参数语义 + 单位 + 边界」,否则 reviewer 看到 4005 range=4.5 无法判断对错。

---

## 8. 时间维度

| 字段 | 来源 | 当前值 | 单位 |
|---|---|---|---|
| `AiProfileCfg.ReactionTimeMs` | tier 1-10 | 1300 → 640 | ms |
| `SliceAiCfg.OverrideReactionTimeMs` | 单切片覆盖 | 同上 | ms |
| `SliceFlowCfg.WaitInputTimeMs` | flow | 守门切片填反应时长,其余 0 | ms |
| `SliceFlowCfg.SaveAngleThresholdDeg` | flow(守门专属) | TBD | 度 |
| `SliceFlowCfg.MaxSaveDistance` | flow(守门专属) | TBD | m? |
| `ReceiveDecisionCfg.DecisionMin/MaxMs` | 接球决策 | 300 / 1000 | ms |

**TBD-14**:`SaveAngleThresholdDeg / MaxSaveDistance` 的具体数值与单位需要程序方确认。

---

## 9. 边界外退化

**TBD-15**:球出界 → 切片直接判失败 / 触发新切片(界外球)?
**TBD-16**:玩家越位检测 = 是 / 否 / 仅特定切片(若 attack 中)?
**TBD-17**:切片超时 → 自动判负 / 给玩家最后一击机会?

---

## 10. 协议变更流程

新增/修改本协议时:
1. 在对应 TBD 项后追加确认结果(填值 + 时间 + 决策人)。
2. 同步更新 `generate_activity_soccer_test_config.py:775` 常量段。
3. 跑 `python scripts/check_xlsx_drift.py` 确认主 xlsx 与新协议一致。
4. 若涉及现有 18 个 preset 的数值,触发一轮回归(跑全套 39 测试 + 端到端冒烟)。

---

## 11. 与本工程其它文档的关系

| 文档 | 关系 |
|---|---|
| `2026世界杯主题活动-开发文档.md` §3.2 | 切片摆位 / 物理参数主案;**冲突时以主案为准**,本协议同步更新 |
| `2026世界杯主题活动-配置表结构.md` | 配置字段 → sheet 列映射;本协议补充每字段单位 |
| `references/feature-spec-writing.md` | 功能策划写作规范 |
| `templates/config-tool-spec.md` §11 自检 | 若未来生成新切片预设,在自检阶段加一步「跑场地协议合规扫」 |
| `output/test-config/level-tags/level_tag_lib.py` | 当前 16 个 tag **不生成空间数据**,本协议暂不影响产物;若未来扩展 patch 写空间数据,必须先消化本协议 |
