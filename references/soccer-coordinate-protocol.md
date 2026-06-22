# 足球场地坐标系协议 · v1(主体已确认 2026-06-18)

> **状态**:v1 主体已确认。剩余 1 项实质 TBD(控球距离起算锚点)+ 2 项 SliceFlowCfg 留空(CamYawRange/CamYawDefault,主案 §3.2 未填)。
> **来源**:从 `output/test-config/generate_activity_soccer_test_config.py` 中 18 个 preset 的实际坐标反推 + 18 项 TBD 程序方/数值方确认(2026-06-18)。
> **用途**:新增切片预设 / 切片实例 / patch 函数 涉及空间数据时,所有人(策划 / 程序 / AI Agent / 关卡 tag 工具)以本协议为准。
>
> **维护约定**:
> - 协议 v1 确认后,主生成器与现存 18 个 preset 数据已按 §12 派生改动清单同步重构;由 `scripts/check_protocol_drift.py` 与 `scripts/check_preset_consistency.py` 守护。
> - 数值变更必须同步更新 `generate_activity_soccer_test_config.py:775` 的常量段。
> - 跑 `python scripts/list_tbd.py` 查所有 references/*.md 的 TBD 当前状态;协议每填完 N 项后建议重跑刷新本头部计数。
> - 本协议与 `2026世界杯主题活动-开发文档.md` §3.2(切片摆位/物理参数)交叉参考;若冲突,以主案为准并同步本协议。

---

## 1. 坐标系基础

### 1.1 单位

✅ TBD-1(2026-06-18):坐标系单位 = **m**。
✅ TBD-1a:全部字段统一为 m,`ReceiveDecisionCfg` 现存 mm/(mm/s) 字段需按 §12 改动 4 折算。

### 1.2 轴向

✅ TBD-2:**home(玩家)进攻方向 = +z**。
- x:左右(横向),正方向 = 进攻方右侧
- y:高度(垂直),0 = 地面
- z:纵深,**+z 指向对方球门**

### 1.3 手系

✅ TBD-3:**右手系**。
- 现有 `_yaw_deg(dx, dz) = atan2(dx, dz)`:以 +z 为 0°,顺时针为正,与 Unity 默认一致。

### 1.4 原点

✅ TBD-4:**原点 (0,0,0) = 对方球门中点**。
- away 球门中心 = (0, 0, 0)
- home 球门中心 = (0, 0, -120)
- 中线 z = -60

### 1.5 facing 角度

✅ TBD-5:facing 范围统一 **[-180, 180]**。
- 0° = 朝 +z(对方球门方向)
- 90° = 朝 +x(右)
- 180° / -180° = 朝 -z(本方球门方向)
- -90° / 270° = 朝 -x(左)

### 1.6 z 取值

✅ TBD-0:**z 坐标允许为负**(原点在对方球门,大部分摆位在 z<0 半场)。
✅ TBD-0a:程序方与数值方共建 `scripts/check_preset_consistency.py`,校验所有 preset BallPos.z / pos.z 在 [-120, 0] 范围内。

---

## 2. 场地几何边界

| 区域 | 边界 |
|---|---|
| 整场 x 范围 | x ∈ [-18, 18] |
| 整场 z 范围 | z ∈ [-120, 0] |
| 球门线(away / home) | z = 0 / -120 |
| 中线 | z = -60 |
| 边线(场地侧) | x = ±18 |

✅ TBD-6 / TBD-7:比赛主要发生在敌方半场 **z ∈ [-60, 0]、x ∈ [-18, 18]**。

```
                +z(对方球门)
                  ↑
                  │
   ┌──────────────┼──────────────┐  away 球门线 (z = 0,原点所在)
   │              │              │
   │   敌方半场    │              │  比赛主要发生区域
   │              │              │
   ├──────────────┼──────────────┤  中线 (z = -60)
   │              │              │
   │   我方半场    │              │
   │              │              │
   └──────────────┼──────────────┘  home 球门线 (z = -120)
                  │
   -x  ←──────────┼──────────→  +x
                  │              (边线 x = ±18)
                 -z
```

---

## 3. 关键功能区

### 3.1 球门

| 字段 | 值 | 单位 |
|---|---|---|
| 球门中心 (away) | (0, 0, 0) | m |
| 球门中心 (home) | (0, 0, -120) | m |
| 球门宽度(立柱间距) | 8.5 | m |
| 球门高度(横梁高) | 3.0 | m |
| 死角厚度 | 0.2 | m |

代码常量 `GOAL_CENTER_X = 0, GOAL_CENTER_Z = 0`(原 `GOAL_CENTER_Z = 58` 错,见 §12 改动 1)。

### 3.2 大禁区

| 字段 | 值 | 单位 |
|---|---|---|
| z 边界 | z = -10 | m |
| x 边界 | x = ±11.5 | m |

大禁区矩形:x ∈ [-11.5, 11.5],z ∈ [-10, 0]。

### 3.3 小禁区

距球门线 **3.5m**。
小禁区矩形:z ∈ [-3.5, 0],x 边界尚未确认(FIFA 标准是球门两侧扩 5.5m,本游戏待程序方填)。

### 3.4 点球点

✅ TBD-8:**点球点 = (0, 0, -11)**。
✅ TBD-8a:开球时弧外其他球员距球 ≥ **9m**(`circle((0,0,-11), 9)` 之外)。

### 3.5 角球点

✅ TBD-9:角旗位置 x = ±18(场地角);角球 BallPos = **(±17, 0, -1)**。

### 3.6 中圈

✅ TBD-10:中圈半径 = **4.5m**。中心在 (0, 0, -60)(中线)。

---

## 4. 球员/物体物理参数

| 参数 | 值 | 单位 | 备注 |
|---|---|---|---|
| 球员碰撞半径 | 0.5 | m | 摆位间距下限 = 2 × 0.5 = 1.0m |
| 球碰撞半径 | 0.2 | m | |
| 球员可控球距离 | 0.5 | m | 见 TBD-18(锚点未明) |
| 默认行走速度 | 2.5 | m/s | `ConstConfig.move_speed_walk` |
| 跑速下限 | 4 | m/s | `ConstConfig.move_speed_run_min` |
| 跑速上限 | 8 | m/s | `ConstConfig.move_speed_run_max` |
| 各倍率 | jog=0.75 / sprint=1.25 / dribble=0.85 / press=1.1 / keeper_lateral=0.9 | 相对 run | `ConstConfig.move_speed_ratio_*` |
| 出球力下限 | 10 | m/s | `ConstConfig.kick_force_min`,即出球初速度 |
| 出球力上限 | 25 | m/s | `ConstConfig.kick_force_max` |

**TBD-18**(剩余实质 TBD):球员可控球距离 0.5m 的**起算锚点**(球员中心 / 脚尖 / 颈部)?当前 0.5m < 球员半径 + 球半径 = 0.7m,若锚点 = 球员中心则与碰撞半径冲突;若锚点 = 脚尖(球员中心向前 0.2-0.3m),则球员中心 → 球中心 ≈ 0.7-0.8m,合理。等程序方明确。

---

## 5. 切片类型 → 法定摆位约束

✅ TBD-11:工具生成新 preset / instance 时,违反以下约束 = **硬错误拒绝生成**。

| SliceType | 约束 |
|---|---|
| 1 attack | BallOwner ∈ home;无越位检测(见 TBD-16) |
| 2 free_kick | 防守方人墙 ≥ 9m 距球;BallOwner ∈ home;**人墙间距 ≥ 1.4m**(2×球员半径 + 球直径,确保球穿过) |
| 3 penalty | 球必须在点球点 (0,0,-11);门将必须在球门线 z=0 ± 死角厚度;其他球员在大禁区外 + 弧外 9m |
| 4 corner | 球必须在 (±17, 0, -1);防守方距球 ≥ 9m |
| 5 throw_in | 球员双脚必须在边线外(`|x| > 18`);头顶双手投掷 |
| 6 goalkeep | 玩家 = 门将,必须在小禁区内(z ∈ [-3.5, 0]);射手必须在球门远端(z 远离 0) |

---

## 6. 镜头与视角

| 字段 | 值 | 单位 |
|---|---|---|
| `CameraFov` | 40-52 度区间(手调) | 度 |
| `SliceFlowCfg.CamYawRange` | 待主案 §3.2 填 | 度 |
| `SliceFlowCfg.CamYawDefault` | 待主案 §3.2 填 | 度 |
| `TargetPoint` | (x, y, z) | m |

✅ TBD-12:**CameraFov 是手调经验值,无公式**。守门切片用 50、任意球用 41-42,按 SliceType 按需调整。

`CamYawRange / CamYawDefault` 当前主案 §3.2 留空,等数值方填(非阻塞 v1)。

---

## 7. AI 行为半径

✅ TBD-13:modifier 参数语义全部明确。

| Modifier | 参数 | 单位 | 备注 |
|---|---|---|---|
| 4001 moving_keeper | speed=1.0, range=2.5 | m/s, m | range = 距门将原始位置的横向半径 |
| 4002 moving_keeper(困难) | speed=1.5, range=3.5 | m/s, m | |
| 4005 moving_keeper(极限) | speed=2.0, range=4.5 | m/s, m | 半径超出球门半宽 4.25m,**允许门将跑出门柱外** |
| 4006 narrow_angle | shrink=0.7 | 倍数 | **`OperableAngle × 0.7`(乘法)**,非减法 |
| 4007 random_dive | randomness=0.6 | [0,1] 概率 | |

---

## 8. 时间维度

| 字段 | 值 | 单位 |
|---|---|---|
| `AiProfileCfg.ReactionTimeMs` | 1300 → 640(tier 1→10 单调下降) | ms |
| `SliceAiCfg.OverrideReactionTimeMs` | 同上,单切片覆盖 | ms |
| `SliceFlowCfg.WaitInputTimeMs` | 守门切片填反应时长,其余 0 | ms |
| `SliceFlowCfg.SaveAngleThresholdDeg` | 15 | 度 |
| `SliceFlowCfg.MaxSaveDistance` | 3 | m |
| `ReceiveDecisionCfg.DecisionMin/MaxMs` | 300 / 1000 | ms |

✅ TBD-14:`SaveAngleThresholdDeg = 15°,MaxSaveDistance = 3m`。

---

## 9. 边界外退化

✅ TBD-15:**球出界 → 切片直接判失败**(不触发界外球切片;界外球切片由其他流程编排)。
✅ TBD-16:**玩家越位检测 = 否**(本游戏简化)。
✅ TBD-17:**切片超时 → 自动判负**(玩家无最后一击机会)。

---

## 10. 协议变更流程

新增/修改本协议时:
1. 在对应 TBD 项后追加确认结果(填值 + 时间 + 决策人)。
2. 若 §1-§4 数值变更,同步更新 `generate_activity_soccer_test_config.py:775` 常量段与 §12 派生改动清单。
3. 跑 `python scripts/check_xlsx_drift.py` 确认主 xlsx 与新协议一致。
4. 跑 `python scripts/list_tbd.py` 刷新协议头部计数。
5. 若涉及现有 18 个 preset 的数值,触发一轮回归(跑全套 39 测试 + 端到端冒烟)。

---

## 11. 与本工程其它文档的关系

| 文档 | 关系 |
|---|---|
| `2026世界杯主题活动-开发文档.md` §3.2 | 切片摆位 / 物理参数主案;**冲突时以主案为准**,本协议同步更新 |
| `2026世界杯主题活动-配置表结构.md` | 配置字段 → sheet 列映射;本协议补充每字段单位与几何含义 |
| `references/feature-spec-writing.md` | 功能策划写作规范 |
| `templates/config-tool-spec.md` §11 自检 | 若未来生成新切片预设,在自检阶段加一步「跑场地协议合规扫」(`check_preset_consistency.py`) |
| `output/test-config/level-tags/level_tag_lib.py` | 当前 16 个 tag **不生成空间数据**,本协议暂不影响产物;若未来扩展 patch 写 PlayersInit/BallPos/TargetPoint,必须先消化本协议 + 落 §12 改动 |

---

## 12. 派生改动清单(代码侧必跟进)

本协议 v1 确认后,主生成器与现存 18 个 preset 数据需要同步重构。当前 P0/P1 已跟进,生成产物需持续通过 `check_protocol_drift.py` / `check_preset_consistency.py` / `check_xlsx_drift.py`。

| # | 改动 | 位置 | 优先级 | 说明 |
|---|---|---|---|---|
| 1 | `GOAL_CENTER_Z = 58 → 0` | `generate_activity_soccer_test_config.py:775` | P0 | 原点改对方球门 |
| 2 | 18 个 preset 的 z 坐标系反转 | `_build_presets:1223+` | P0 | 现 17 个 preset z∈[30,58](错),preset 1 z∈[-30,-5](对);全部按本协议改为 z∈[-60,0] 量级 |
| 3 | `ConstConfig.ball_control_distance = 1.2 → 0.5` | `actv_soccer_const_rows` | P0 | 协议 §4 |
| 4 | `ReceiveDecisionCfg` 8 字段单位转 m/(m/s) | initial 4 行 `Step/Style/Distance/Speed/Height` | P0 | SafeDistance / HighPressureDistance / ForwardProbeDistance / SideProbeDistance / BackwardProbeDistance / HighBallHeight / FastBallSpeed(从 mm/(mm/s) 折算) |
| 5 | 任意球人墙间距 1.0m → ≥ 1.4m | `_build_presets._free_kick_wall` | P0 | 协议 §5(2×球员半径 + 球直径,球能穿过) |
| 6 | 点球点 (0,0,50) → (0,0,-11) | preset 3 / 9 | P0 | 协议 §3.4 |
| 7 | 角球 BallPos (±20,0,58) → (±17,0,-1) | preset 10 / 11 / 18 | P0 | 协议 §3.5 |
| 8 | 大禁区数值代入(z=-10, x=±11.5) | 校验工具未来用 | P1 | |
| 9 | 主生成器顶部加坐标系常量段(原点 / 单位 / 手系 / 场地边界 / 关键功能区) | 文件头部 | P1 | self-documenting,引用本协议 |
| 10 | 落 `scripts/check_preset_consistency.py` | `scripts/` | P1 | 协议 TBD-0a:校验所有 preset 与本协议合规 |
| 11 | 关卡 tag 工具:`level_tag_lib.PatchContext.library` 字段补一个 `protocol_v1` 子键 | `level_tag_lib.py` | P2 | 未来 patch 写空间数据时直接读 |

当前 P0/P1 已完成并由脚本校验。后续若扩展 tag patch 写 BallPos / PlayersInit / TargetPoint,必须先消化本协议并补充对应校验用例。
