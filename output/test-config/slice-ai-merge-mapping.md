# ActvSoccerSliceAiCfg 合并到 ActvSoccerSliceInstanceCfg 映射方案

## 目标

`ActvSoccerSliceAiCfg` 不再作为独立配置表输出。原表中所有 AI 绑定字段并入 `ActvSoccerSliceInstanceCfg`，程序通过 `LevelCfg.SliceList[] -> SliceInstanceCfg.ID` 一次读取切片结构、目标、机制和 AI 参数。

## 表级变化

| 旧表 | 新表 | 处理 |
| --- | --- | --- |
| `ActvSoccerSliceAiCfg` | `ActvSoccerSliceInstanceCfg` | 删除独立表，字段并入实例表 |
| `ActvSoccerSliceInstanceCfg` | `ActvSoccerSliceInstanceCfg` | 保留原字段，并新增 AI 字段 |

## 字段映射

| 旧字段 | 新字段 | 说明 |
| --- | --- | --- |
| `ActvSoccerSliceAiCfg.SliceID` | `ActvSoccerSliceInstanceCfg.ID` | 原反向关联消失，直接在实例行上读取 |
| `AiProfileID` | `AiProfileID` | 难度档，仍引用 `ActvSoccerAiProfileCfg.ID` |
| `GoalkeeperAiID` | `GoalkeeperAiID` | 门将 AI，仍引用 `ActvSoccerEnemyAiCfg.ID`，`0` 表示无 |
| `DefenderAiID` | `DefenderAiID` | 后卫 AI，仍引用 `ActvSoccerEnemyAiCfg.ID`，`0` 表示无 |
| `ShooterAiID` | `ShooterAiID` | 射手 AI，主要用于守门切片，`0` 表示无 |
| `ModifierID` | `ModifierID` | 切片机制，仍引用 `ActvSoccerAiModifierCfg.ID`，`0` 表示无 |
| `IsGuideAi` | `IsGuideAi` | 引导/试训 AI 标记 |
| `RewindRandom` | `RewindRandom` | 回溯后是否重新随机 |
| `OverrideReactionTimeMs` | `OverrideReactionTimeMs` | 单切片反应时间覆盖，`0` 表示使用默认值 |
| `ActvSoccerSliceAiCfg.ID` | 删除 | 不再需要单独 AI 配置 ID |
| `ActvSoccerSliceAiCfg.Remark` | `ActvSoccerSliceInstanceCfg.Remark` | 备注合并到实例行，不保留独立 AI 备注 |

## 程序读取链路

旧链路：

```text
LevelCfg.SliceList[]
  -> SliceInstanceCfg.ID
  -> SliceAiCfg.SliceID == SliceInstanceCfg.ID
  -> AiProfile / EnemyAi / Modifier
```

新链路：

```text
LevelCfg.SliceList[]
  -> SliceInstanceCfg.ID
  -> 直接读取 SliceInstanceCfg 上的 AiProfileID / EnemyAiID / ModifierID
```

## 运行时语义

- `GoalkeeperAiID = 0`：该切片不启用门将 AI。
- `DefenderAiID = 0`：该切片不启用后卫 AI。
- `ShooterAiID = 0`：该切片不启用对方射手 AI。
- `ModifierID = 0`：无切片级额外机制。
- `IsGuideAi = 1`：引导/试训切片，程序可按引导逻辑处理。
- `RewindRandom = 1`：回溯后随机种子应包含 `rewind_count`。
- `OverrideReactionTimeMs = 0`：使用 `AiProfileCfg.ReactionTimeMs`；非 0 时优先使用实例覆盖值。

## Tag 工具输出边界

关卡 tag 工具 `output/test-config/level-tags/apply_level_tags.py` 现在只输出：

- `ActvSoccerLevelCfg`
- `ActvSoccerSliceInstanceCfg`

modifier 类 tag 会复制 `SliceInstanceCfg` 行，分配 `>=90000` 的虚拟实例 ID，并直接修改新实例行上的 `ModifierID`。不再生成或复制 `ActvSoccerSliceAiCfg` 行。

## 兼容检查

程序侧需要删除以下假设：

- 不再加载 `ActvSoccerSliceAiCfg`。
- 不再通过 `SliceAiCfg.SliceID` 反查 AI。
- 不再依赖 `SliceAiCfg.ID`。

程序侧需要新增或确认：

- `ActvSoccerSliceInstanceCfg` 解析新增 AI 字段。
- `LevelCfg.SliceList[]` 中每个 ID 直接对应一条 `SliceInstanceCfg`。
- `>=90000` 的虚拟实例和普通实例读取方式一致。
