# PRD - Mini Soccer Star 风格接球决策系统配置说明

**日期**：2026-06-15  
**用途**：给策划补充接球决策相关配置，后续程序按本说明接入工程现有 Soccer 框架。  
**适用范围**：联赛 > 关卡 > 切片组内，非玩家操作阶段的 AI 接球、友方接球后进入操作态前的第一脚触球规划。

---

## 1. 配置目标

本次配置不是做完整足球模拟器，而是让 AI 接球前就能决定第一脚处理方式。

期望表现：

- 球飞行中，AI 已经开始判断落点、空间、防守压力。
- 接球第一脚不是固定停球，而是根据局势选择领球、护球、半转身、一脚传球或一脚射门。
- 玩家看到的结果应像“球员提前知道下一步要做什么”。

---

## 2. 策划需要补的配置

本需求建议新增 3 类配置：

| 配置表 | 作用 | 是否 P0 |
|---|---|---|
| `ActvSoccerReceiveDecisionCfg` | 接球决策主配置，控制决策窗口、评分权重、动作倾向 | 是 |
| `ActvSoccerPlayerStyleCfg` | 球员风格配置，定义 Playmaker / Dribbler / TargetMan 的差异 | 是 |
| `ActvSoccerFirstTouchAnimCfg` | 第一脚触球表现选择配置，用于动作逻辑和动画解耦 | P1 |

也可以把 `ReceiveDecisionCfgID` 挂到现有球员/角色配置表中。如果当前表结构暂时不方便改，程序会先按角色兜底：

| 角色 | 默认风格 |
|---|---|
| MID | Playmaker |
| FWD | Dribbler |
| DEF | Balanced |
| GK | 不参与普通接球决策 |

---

## 3. 配置表规则

客户端配置表第一行只能是 `ID`。

示例中第一列均为 `ID`。枚举字段建议使用英文枚举值，避免程序解析中文文案。

推荐单位：

| 类型 | 单位 |
|---|---|
| 时间 | 毫秒 |
| 距离 | 毫米 |
| 角度 | 度 |
| 权重 | 整数，100 为标准值 |
| 分数 | 整数 |

---

## 4. `ActvSoccerReceiveDecisionCfg`

### 4.1 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `ID` | int | 配置 ID |
| `Style` | string | 默认球员风格：`Balanced` / `Playmaker` / `Dribbler` / `TargetMan` |
| `DecisionMinMs` | int | 最早决策时间，球预计接触前多少毫秒开始允许生成决策，建议 300 |
| `DecisionMaxMs` | int | 最晚决策时间，球预计接触前多少毫秒内必须已有决策，建议 1000 |
| `SafeDistance` | int | 安全距离，最近防守人距离大于该值时视为低压 |
| `HighPressureDistance` | int | 高压距离，最近防守人距离小于该值时视为高压 |
| `ForwardProbeDistance` | int | 分析前方空间的探测距离 |
| `SideProbeDistance` | int | 分析左右空间的探测距离 |
| `BackwardProbeDistance` | int | 分析身后空间的探测距离 |
| `HighBallHeight` | int | 高空球高度阈值，超过后表现层优先胸停/头球类动作 |
| `FastBallSpeed` | int | 高速来球速度阈值，超过后提高停球权重 |
| `StopWeight` | int | 停球权重 |
| `PushForwardWeight` | int | 顺势向前领球权重 |
| `PushSideWeight` | int | 左右领球权重 |
| `HalfTurnWeight` | int | 半转身权重 |
| `ShieldWeight` | int | 护球权重 |
| `OneTouchPassWeight` | int | 一脚传球权重 |
| `OneTouchShotWeight` | int | 一脚射门权重 |
| `SpaceGainWeight` | int | 评分项：空间收益权重 |
| `GoalProgressWeight` | int | 评分项：向球门推进权重 |
| `SafetyWeight` | int | 评分项：安全性权重 |
| `FlowWeight` | int | 评分项：是否利于下一步动作 |
| `StyleBonusWeight` | int | 评分项：球员风格加成 |
| `Remark` | string | 策划备注 |

### 4.2 配置示例

| ID | Style | DecisionMinMs | DecisionMaxMs | SafeDistance | HighPressureDistance | ForwardProbeDistance | SideProbeDistance | BackwardProbeDistance | HighBallHeight | FastBallSpeed | StopWeight | PushForwardWeight | PushSideWeight | HalfTurnWeight | ShieldWeight | OneTouchPassWeight | OneTouchShotWeight | SpaceGainWeight | GoalProgressWeight | SafetyWeight | FlowWeight | StyleBonusWeight | Remark |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | Balanced | 300 | 1000 | 3500 | 1600 | 5000 | 3500 | 2500 | 900 | 16000 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 通用默认 |
| 2 | Playmaker | 300 | 1000 | 3500 | 1700 | 4500 | 3500 | 2500 | 900 | 16000 | 90 | 90 | 90 | 100 | 80 | 140 | 100 | 90 | 110 | 100 | 130 | 130 | 组织核心，倾向一脚传球 |
| 3 | Dribbler | 300 | 1000 | 3200 | 1500 | 5500 | 4000 | 2500 | 900 | 16000 | 80 | 140 | 130 | 120 | 90 | 80 | 110 | 130 | 120 | 90 | 120 | 130 | 突破手，倾向顺势领球 |
| 4 | TargetMan | 300 | 1000 | 3000 | 1400 | 4000 | 3000 | 3000 | 900 | 15000 | 120 | 80 | 80 | 110 | 150 | 100 | 120 | 80 | 100 | 140 | 110 | 130 | 支点，倾向护球和背身处理 |

---

## 5. `ActvSoccerPlayerStyleCfg`

### 5.1 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `ID` | int | 配置 ID |
| `Style` | string | 风格枚举：`Balanced` / `Playmaker` / `Dribbler` / `TargetMan` |
| `ReceiveDecisionCfgID` | int | 引用 `ActvSoccerReceiveDecisionCfg.ID` |
| `PassBias` | int | 传球倾向，100 为标准 |
| `DribbleBias` | int | 盘带/领球倾向，100 为标准 |
| `ShieldBias` | int | 护球倾向，100 为标准 |
| `ShotBias` | int | 射门倾向，100 为标准 |
| `RiskBias` | int | 风险倾向，越高越敢做高收益低安全动作 |
| `Remark` | string | 策划备注 |

### 5.2 配置示例

| ID | Style | ReceiveDecisionCfgID | PassBias | DribbleBias | ShieldBias | ShotBias | RiskBias | Remark |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Balanced | 1 | 100 | 100 | 100 | 100 | 100 | 通用 |
| 2 | Playmaker | 2 | 140 | 90 | 80 | 100 | 105 | 德布劳内/莫德里奇类 |
| 3 | Dribbler | 3 | 80 | 140 | 90 | 110 | 120 | 梅西/姆巴佩类 |
| 4 | TargetMan | 4 | 100 | 80 | 150 | 120 | 90 | 哈兰德/凯恩类 |

---

## 6. 球员表扩展建议

如果当前球员或角色配置表允许扩展，建议增加字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `PlayerStyleCfgID` | int | 引用 `ActvSoccerPlayerStyleCfg.ID` |

如果暂时不加字段，程序会用角色兜底。兜底规则见第 2 节。

---

## 7. `ActvSoccerFirstTouchAnimCfg`

该表用于表现层，P1 可做。核心要求是：逻辑动作不直接绑定固定动画。

动画选择需要由以下输入共同决定：

- `Action`
- `BallHeightType`
- `BallDirectionType`
- `BodyDirectionType`
- `PressureLevel`

### 7.1 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `ID` | int | 配置 ID |
| `Action` | string | `Stop` / `PushForward` / `PushLeft` / `PushRight` / `HalfTurnLeft` / `HalfTurnRight` / `Shield` / `OneTouchPass` / `OneTouchShot` |
| `BallHeightType` | string | `Ground` / `High` |
| `BallDirectionType` | string | `Front` / `Left` / `Right` / `Back` |
| `BodyDirectionType` | string | `FaceBall` / `BackToBall` / `SideToBall` |
| `PressureLevel` | string | `Low` / `Medium` / `High` / `Any` |
| `StateKey` | string | 对应 `ActvSoccerCharacterStateCfg.StateKey`，例如 `Control` / `Pass` / `Kick` / `Stop` / `TurnLeft` / `TurnRight` |
| `AnimKey` | string | 美术动作 Key，优先匹配已有动作表 |
| `Priority` | int | 多条命中时取优先级高的 |
| `Remark` | string | 策划备注 |

### 7.2 配置示例

| ID | Action | BallHeightType | BallDirectionType | BodyDirectionType | PressureLevel | StateKey | AnimKey | Priority | Remark |
|---|---|---|---|---|---|---|---|---:|---|
| 1 | Stop | Ground | Front | FaceBall | Any | Control | B01_ReceiveBall | 100 | 地面正面停球 |
| 2 | Stop | High | Front | FaceBall | Any | Control | B03_ReceiveAir | 100 | 高空球停球，可复用 B01 |
| 3 | PushForward | Ground | Front | FaceBall | Low | Control | B02_DribbleTouch | 110 | 顺势领球推进 |
| 4 | PushLeft | Ground | Front | FaceBall | Low | Control | B02_DribbleTouch | 100 | 左侧领球，表现可镜像 |
| 5 | PushRight | Ground | Front | FaceBall | Low | Control | B02_DribbleTouch | 100 | 右侧领球，表现可镜像 |
| 6 | HalfTurnLeft | Ground | Back | BackToBall | Medium | TurnLeft | A05_TurnLeft | 100 | 背身半转身 |
| 7 | HalfTurnRight | Ground | Back | BackToBall | Medium | TurnRight | A06_TurnRight | 100 | 背身半转身镜像 |
| 8 | Shield | Ground | Back | BackToBall | High | Control | B01_ReceiveBall | 120 | 高压背身护球，后续可替换专用护球动作 |
| 9 | OneTouchPass | Ground | Front | FaceBall | Low | Pass | C03_OneTouchPass | 120 | 一脚传球 |
| 10 | OneTouchShot | Ground | Front | FaceBall | Low | Kick | D01_Shoot | 100 | 一脚射门，可复用射门动作 |
| 11 | OneTouchShot | High | Front | FaceBall | Any | Kick | D05_Volley | 110 | 高空球一脚处理，后续可扩展头球/倒挂金钩 |

---

## 8. 第一脚动作枚举说明

| 动作 | 说明 | 典型场景 |
|---|---|---|
| `Stop` | 缓冲停球，降低球速后进入下一步 | 高速来球、空间不足 |
| `PushForward` | 向进攻方向顺势领球 | 前方空间大 |
| `PushLeft` | 向左侧空间领球 | 左侧空间更大 |
| `PushRight` | 向右侧空间领球 | 右侧空间更大 |
| `HalfTurnLeft` | 左半转身接球 | 背身接球，左侧可转身 |
| `HalfTurnRight` | 右半转身接球 | 背身接球，右侧可转身 |
| `Shield` | 护球，优先保护球权 | 后卫贴身、高压 |
| `OneTouchPass` | 一脚传球 | 队友空位、组织型球员 |
| `OneTouchShot` | 一脚射门 | 禁区前沿、射门路线清晰 |

后续可扩展：

| 动作 | 说明 |
|---|---|
| `ChestControl` | 胸部停球 |
| `HeaderPass` | 头球摆渡 |
| `HeaderShot` | 头球射门 |
| `BicycleKick` | 倒挂金钩 |

MVP 阶段不建议把高空球动作拆成独立逻辑动作，优先由表现层根据球高度选择动画。

---

## 9. 验收场景与配置关注点

| 场景 | 配置关注点 | 预期结果 |
|---|---|---|
| A：前方大量空间 | `PushForwardWeight`、`SpaceGainWeight`、`ForwardProbeDistance` | AI 顺势向前领球 |
| B：背身接球，后卫贴身 | `HighPressureDistance`、`ShieldWeight`、`HalfTurnWeight`、`SafetyWeight` | AI 优先护球或转身 |
| C：禁区前沿，队友空位 | `OneTouchPassWeight`、`PassBias`、`FlowWeight` | Playmaker 优先一脚传球 |
| D：高速来球 | `FastBallSpeed`、`StopWeight`、`SafetyWeight` | AI 优先缓冲停球 |
| E：高空球 | `HighBallHeight`、`ActvSoccerFirstTouchAnimCfg` | 表现层优先胸停、头球或凌空处理 |

---

## 10. 和现有切片操作的关系

当前玩法中，玩家不是直接控制球员移动，而是在可操作态控制球的运动参数。

因此配置需要遵守：

- AI 可以在球飞行中提前规划第一脚触球。
- 我方球员接球后，如果该接球点需要进入玩家操作态，则第一脚决策只负责朝向、轻微领球、表现动作，不自动替玩家传球或射门。
- 非玩家操作阶段的 AI 球员，才允许执行 `OneTouchPass` / `OneTouchShot` 自动出球。
- 友方接球后仍需要满足现有“可操作夹角扇形覆盖合法目标”的规则；如果最大夹角无法覆盖队友或球门，则先带球调整方向。

---

## 11. 策划确认项

| 编号 | 问题 | 建议 |
|---|---|---|
| 1 | 球员风格是否挂到具体球员，还是先按角色兜底 | 建议具体球员可配，角色兜底 |
| 2 | `OneTouchPass` 在玩家可操作接球点是否允许自动触发 | 建议不自动触发，只作为朝向和表现参考 |
| 3 | 高空球 MVP 是否只做表现层区分 | 建议 MVP 只做表现层，后续再扩展头球/倒挂金钩逻辑 |
| 4 | 风格权重是否允许关卡覆盖 | 建议 P1 支持切片组 modifier 覆盖 |
| 5 | 压力距离是否全局统一 | 建议先按风格配置，必要时后续按关卡难度覆盖 |

