# Audio Demand Splitting

原始策划文档不能直接跳过需求拆分而写正式配置意图。先产出策划和音频人员可审核的 `audio_demand.xlsx`,确认触发点、复用关系和制作范围后,再同步到 `audio_sheet.xlsx`。

`audio_demand.xlsx` 是正式生产前的策划审核闸口,不是内部临时文件。没有策划/音频负责人确认前,不得继续公司库检索、AI 生成、候选试听或最终交付。

## 拆分范围

只拆玩家能听到的触发:

- UI 打开 / 关闭。
- 按钮、确认、取消、选择和不可用反馈。
- 奖励、稀有度、状态变化和动画/VFX 同步点。
- 滚动、蓄力、机器、环境等循环;循环必须标记 StopEvent。
- 3D/world 的释放、命中、弹道、冲击、出生和死亡。

不要把 DropID、概率、消耗 ID、文本 key、后端状态或算法字段直接拆成音效。

## K1 项目额外规则

当 `project` 为 `K1` 或用户/文档明确为 K1 项目时：

1. **拆需求前**先完成 `references/k1-audio-library.md` 复用检查（详见 `references/naming-and-reuse.md` K1 章节）。
2. `asset` 可填 AudioList ID 或文件名；JSON 中保留查到的 `const_name`/备注到 `notes` 字段（如有）。
3. 常规 UI 反馈、奖励、宝箱、升级、错误、地图/行军、BGM 优先 `复用`；活动玩法、角色技能、强主题包装才 `新增`。
4. 索引过旧时运行：

```bash
python scripts/build_k1_audio_library.py --project-root <K1仓库根> --output references/k1-audio-library.md --json-output references/k1-audio-library.json
```

5. K1 仅拆需求时按 `k1-demand-only.md` 生成和验收；其必填字段、零需求与复用规则优先于下方生产字段要求。后续进入生产流水线时再统一工程命名与 `sheetName`，不把 X15 生产规范直接套给 K1。

## Demand JSON Schema

`build_production_package.py` 和 `generate_audio_demand_workbook.py` 消费以下结构:

```json
{
  "project": "X15",
  "sheets": [
    {
      "name": "DragonLandRandomConsume",
      "note": "需求来源与范围说明",
      "rows": [
        {"type": "module", "name": "地龙局内随机与消耗"},
        {"type": "submod", "name": "三选一"},
        {
          "t": "2D",
          "event": "ui_rogue_choice_refresh_free",
          "tag": "新增",
          "asset": "ui_rogue_choice_refresh_shuffle",
          "desc": "轻纸牌洗牌和快速重排,不做奖励感",
          "prompt": "short light paper-card shuffle...",
          "bank": "RogueTower",
          "module": "RogueTower",
          "trigger": "免费刷新成功时",
          "priority": "P0",
          "loop": "FALSE",
          "stop_event_needed": "FALSE",
          "library_queries": ["light paper card shuffle", "quick card flutter soft tap"]
        }
      ]
    }
  ]
}
```

## 必填字段

每个真实需求行必须包含:

- `event`: 程序触发事件名。
- `tag`: `新增`、`复用` 或 `沿用X1`。
- `asset`: 真实音频资源名。
- `desc`: 声音说明;新增必填。
- `bank` / `module`: 资源归属。
- `trigger`: 精确触发时机。
- `priority`: `P0`、`P1` 或 `P2`。
- `loop`: 是否循环。
- `stop_event_needed`: 是否需要程序调用 StopEvent。

新增行还必须包含 `prompt` 和至少一个 `library_queries` 查询词。循环行必须同时满足 `loop=TRUE` 和 `stop_event_needed=TRUE`。

## 复用不是模拟占位

`复用` 只能用于已经验证存在的 X15/公司音频资源。不能因为一个名字看起来像通用资源,就直接写 `复用 common_xxx`。

X1 若仍是 Wwise 资源、命名体系或导出方式与 X15 不一致,默认不能直接视为可复用资源。只有完成导出/转码/命名映射并确认 X15 程序能按 `audio/<asset>.ogg` 使用后,才允许写 `沿用X1` 或 `复用`。

如果本期需要先建立一条未来可复用的通用音效,例如 `common_item_select`,做法是:

- 第一轮把该资源按 `新增` 处理,`asset` 可以命名为 `common_item_select`。
- 在 `notes` 或描述中写明「本轮新建通用复用资产」。
- 它进入公司库检索、AI gap、候选试听和最终 WAV/OGG 交付。
- 只有它真实落成并通过交付校验后,后续需求才可以写 `复用 common_item_select`。

不要使用“复用但本次需要生成”这种口头状态。工具里的真实状态是:

| 情况 | `tag` | 资源状态 |
|------|-------|----------|
| 已验证存在的 X15/公司资源 | `复用` | `reuse_verified` |
| 已验证完成迁移的 X1 资源 | `沿用X1` | `reuse_verified` |
| 本轮要先做出来、以后复用的 common 资源 | `新增` | `pending_company_library` / `generated` |
| 只写了 common 名但没找到真实资源 | 不允许当完成 | `reuse_unverified` 并阻塞 |

## 资产级复用

同一个 asset 可以被多个事件引用。如果任一事件把该 asset 标为 `新增`,资产层面只制作一次;其他引用行只是复用这份本轮新资源。公司库检索、AI gap、WAV 制作和 OGG 转码都只能排一次。

`复用` / `沿用X1` 必须验证目标 OGG 或正式资源记录真实存在。只有写了 common 名称但没有找到资源时,状态应为 `reuse_unverified`,不能视为完成。

## 审核边界

`audio_demand.xlsx` 是人类审核面;`audio_sheet.xlsx` 是配置意图面。两者职责不同,都需要保留:

- Demand: 生产状态、优先级、Prompt、Loop/StopEvent、策划/音频验收。
- Audio sheet: Event/Asset/功能模块/声音类型/描述/触发时机和配置覆盖列。

策划审核至少检查:

- 是否漏拆玩家能听到的关键触发点。
- 普通 UI 反馈是否正确复用,有没有过度新增。
- `新增/复用/沿用X1` 判断是否符合本期制作范围。
- Event/Asset 命名是否能给程序和音频端直接使用。
- Loop 行是否标了 StopEvent。
- Prompt/描述是否符合策划想要的表现方向。
- 优先级是否合理。
