---
name: audio-production-pipeline
description: X15/K1 音效需求拆分、音频生产和配置意图流程。用于把策划/程序文档先拆成可审核的 audio_demand.xlsx，再进行公司库检索、试听决策、AI 缺口生成、WAV/OGG 交付，并把完整配置意图写入 .gdconfig_tmp/output/audio/audio_sheet.xlsx 的指定 sheetName。K1 项目拆需求前必须先查 references/k1-audio-library。触发词：拆音效、生成音效需求、声音设计文档、音效库、复用音效、K1音效、audio production。K1 仅拆需求不要求生产 sheetName；进入完整生产流水线时必须指定 sheetName。
---

# Audio Production Pipeline

## 模式入口（先判定）

K1 的“音效需求／拆需求／派生需求文档”默认进入 [K1 独立需求模式](references/k1-demand-only.md)，读取该文件及音效库后直接生成需求文档。该模式不要求 X15 工作区、生产包、audio_sheet.xlsx、API 或生产用 sheetName；下文工作区、全部必产文件、prepared/review-ready/handoff-ready 校验和生产阶段步骤均不适用。用户明确要求音频生产或配置意图时，才进入下文完整流水线并确认 sheetName。

本 skill 负责“声音怎么产出”和“这条声音的配置意图是什么”。它面向需求理解、音频选型、AI 生成和音频端交付，最终把已经推断完成的音效配置意图写入 `audio_sheet.xlsx`。

它不生成正式 XCfg 配置，不导入 Unity 资源，不生成 DisplayKey。后续落地由 sibling skill `audio-config-pipeline` 消费同一个 `sheetName` 完成。

## 第一次使用先读

第一次使用、策划自助使用、或排查别人运行记录时,先读 `references/first-run-workflow.md`。本流程有严格闸门,不能把脚本从上到下随便跑一遍:

```text
需求拆分 -> 策划审核 -> API 配置 -> 公司库/AI 候选 -> 试听决策 -> OGG 交付
```

每一步只在前一阶段校验通过后继续。`pending_planner_review`、缺 token、无候选、dry-run 缺 WAV、缺决策导致的失败通常是流程未到位,不是工具坏。

## 工作区定位

所有命令以工作区根目录为基准。工作区根目录必须同时包含：

```text
.gdconfig_tmp
audio
client
```

不同人的盘符可以不同，但后续结构保持一致：

```text
<workspaceRoot>/
  .gdconfig_tmp/
  audio/
  client/
```

如果当前在 `<workspaceRoot>/client`，先回到上一级工作区根。

## 项目识别

| 项目 | 识别条件 | 复用检查 |
|------|----------|----------|
| **X15** | 工作区含 `.gdconfig_tmp` + `audio` + `client`，或用户明确说 X15 | 查工作区 `audio/<asset>.ogg`、公司库、X1 迁移规则 |
| **K1** | 文档/用户说明含 `K1`、`K1项目`、`K1项目组`，或工作区为 K1 client | **必须先查** `references/k1-audio-library.md` 与 `references/k1-audio-library.json` |

本 skill 已整合原 `sound-design-splitter`（拆需求 + K1 复用库）和 `slg-sfx-generation-workflow`（公司库/AI/交付）的全部职责；不要再分别调用那两个旧 skill。

### K1 音效库复用检查

当项目为 K1 时，在生成 demand JSON 之前必须执行：

1. 读取 `references/k1-audio-library.md` 的「常用复用入口」和「分类索引」。
2. 精确查 ID、文件名、常量名或备注时，检索 `references/k1-audio-library.json`；不要凭记忆判断。
3. 若 K1 仓库音频资源可能已更新，可刷新索引：

```bash
python scripts/build_k1_audio_library.py --project-root <K1仓库根目录> --output references/k1-audio-library.md --json-output references/k1-audio-library.json
```

4. 对每条需求按「触发时机 + 声音语义 + 文件名/备注关键词」查库：
   - 命中同类资源 → 标注 `复用`，`asset` 填已有 AudioList ID 或文件名。
   - 语义不匹配、主题包装不同、或需全新玩法表现 → 标注 `新增`。
   - 不确定时写候选 ID/文件名，并注明「需人工试听确认」。
5. K1 常规 UI、奖励、宝箱、升级、错误提示、地图行军、BGM/环境优先复用；活动玩法、角色技能、强主题包装才考虑新增。

K1 常用语义 → 查库方向见 `references/k1-audio-library.md`「常用复用入口」；完整规则见 `references/naming-and-reuse.md` 的 K1 章节。

## 核心输出

第一个主输出是策划/音频可审核的需求拆分表:

```text
.gdconfig_tmp/output/audio/production/<sheetName>/audio_demand.xlsx
```

它必须明确 `新增/复用/沿用X1`、优先级、Bank/模块、Loop/StopEvent、制作方向和验收列。原始 docx 不能直接跳过这一层。规则与 JSON schema 见 `references/demand-splitting.md`。

第二个主输出是配置意图表:

```text
.gdconfig_tmp/output/audio/audio_sheet.xlsx
```

一个 workbook 可以有多个 sheet。每个 `sheetName` 对应一个功能、任务、分支或负责人。

`audio_sheet.xlsx` 不是原始需求表，也不是正式配置表的完整复制。它是中间层：

```text
原始需求
  ↓ audio-production-pipeline 做 AI 语义推断
audio_sheet.xlsx（配置意图表）
  ↓ audio-config-pipeline 做规则展开
正式 XCfg 音频配置
```

除主输出外，每次跑流程都必须在 `.gdconfig_tmp/output/audio/production/<sheetName>/` 下产出完整的生产端辅助产物集合（不是按需，是默认必出）。具体清单见 `references/repo-paths.md` 的「必产文件」章节。这些产物不作为客户端配置落地的源数据，但是音频生产、试听评审、AI 生成与最终交付不可或缺的工作件。

## 强约定

- 用户必须指定 `sheetName`。
- 如果用户没有指定 `sheetName`，先问：`这条音频生产流程要求指定 audio_sheet.xlsx 里的 sheetName。请告诉我要处理哪个 sheet。`
- 禁止默认 `Sheet1`、第一个 sheet 或历史 sheet。
- 一个 sheet 内 `事件名` 必须唯一。
- 原始策划文档必须先拆成 demand JSON 和 `audio_demand.xlsx`,不允许直接跳到公司库、AI 或正式配置。
- `audio_demand.xlsx` 必须先交给策划/音频负责人审核。未确认前,禁止进入公司库检索、AI 生成、候选试听页和最终交付。
- `planner_demand_review.json` 的 `status` 必须从 `pending_planner_review` 改为 `approved` 后,才允许运行公司库检索。临时技术验证必须显式使用 bypass 参数并在汇报中说明。
- `复用` 只能写已验证存在的 X15/公司音频资源。不能用 `common_xxx` 模拟复用;未生成的通用音效必须先按 `新增` 生产成真实资源,之后才允许后续复用。
- X1/Wwise 资源默认不能直接复用。只有完成导出、转码、命名映射和 X15 可播放验证后,才允许写 `沿用X1` 或 `复用`。
- 一行代表一个完整配置意图。
- 如果多个事件复用同一个音频文件，`音效资源名` 必须完全相同。
- `新增` / `复用` / `沿用X1` 是生产状态,不是事件是否存在的判断。`复用` 和 `沿用X1` 不算未完成,必须进入交付清单,但不能进入普通 AI 生成队列。
- `audio_sheet.xlsx` 必须保留 `生产状态`、`优先级`、`是否循环`、`需StopEvent` 和 `资源状态`,防止生产真相只存在于自由文本。
- 必须完成“需求语义 -> 配置意图”的 AI 推断，不能把这一步留给 `audio-config-pipeline`。
- 不要铺满正式配置的所有列；只写基础列和必要可选列。
- 能由 `声音类型` 默认规则稳定表达的信息，不额外填列。
- 不能由 `声音类型` 稳定表达、或需要偏离默认值的信息，必须在同一行补可选列。
- 每次跑流程都必须默认创建 `.gdconfig_tmp/output/audio/production/<sheetName>/` 目录及其下的全部必产文件（见 `references/repo-paths.md`）。不要等用户主动要才生成；目录不存在就自动创建。即使是简单需求、复用资源较多、或还没有 WAV 交付，所有清单文件也都要落盘（用空模板 / 占位结构 / pending 状态表达即可）。

## 基础列

默认工作表只包含基础列：

| 列名 | 说明 |
|------|------|
| `事件名` | 程序触发名，对应 `AudioEvent.事件名`。使用 lowercase snake_case，不带 `Play_` / `Stop_` 前缀 |
| `音效资源名` | 音频文件名，不含扩展名。生产端 WAV 和最终 OGG 都必须使用这个名字，后续落地流水线按 `audio/<音效资源名>.ogg` 查找资源 |
| `功能模块` | Unity 资源落地目录名，对应 `client/Assets/X1/Res/Audio/Ogg/<功能模块>/` |
| `声音类型` | AI 语义推断结果，用于后续固定推导总线、播放模式、循环、2D/3D |
| `描述` | 声音设计说明，也会合并进正式配置备注 |
| `触发时机` | 程序接入说明，也会合并进正式配置备注 |

## 声音类型

| 声音类型 | 默认含义 |
|----------|----------|
| `UI一次性` | UI 按钮、弹窗、提示等短促一次性声音 |
| `2D音效` | 无位置的普通一次性音效 |
| `3D音效` | 场景内有位置的一次性音效 |
| `Sfx循环` | 无位置的 Sfx 循环 |
| `3D循环` | 场景内有位置的 Sfx 循环 |
| `环境循环` | 风、雨、场景氛围等环境循环 |
| `音乐循环` | BGM 或主题音乐循环 |
| `语音` | 角色语音、旁白 |

如果这些默认含义已经能完整表达需求，不要再铺 `总线`、`播放模式`、`是否循环`、`空间混合` 等正式配置列。如果默认含义不够，才在同一行增加 `总线`、`播放模式`、`空间混合`、`音量` 等覆盖列。

## 推断边界

`audio-production-pipeline` 做 AI 语义推断，必须回答这些问题：

- 这是 UI、2D、3D、循环、环境、音乐还是语音？
- 是否需要 Switch / State / Parameter？
- 是否偏离默认音量、距离、优先级、最大实例数、淡入淡出？
- 是否需要多个事件复用同一个音频资源？
- 业务触发时机是否足以支撑程序接入？

`audio-production-pipeline` 不需要把所有正式配置字段都写进 sheet。正确输出是“刚刚好够用”：

| 需求 | sheet 应该表达 |
|------|----------------|
| 普通 UI 点击 | 基础列 + `声音类型=UI一次性` |
| UI 点击要更轻 | 基础列 + `声音类型=UI一次性` + `音量=0.6` |
| 普通 3D 音效 | 基础列 + `声音类型=3D音效` |
| 3D 音效听得更远 | 基础列 + `声音类型=3D音效` + `最大距离=80` |
| 草地脚步变体 | 基础列 + `声音类型=3D音效` + `Switch源事件名` + `Switch条件` |

如果只靠基础列无法表达完整配置意图，就必须补可选列。不要期望 `audio-config-pipeline` 从 `描述` 或 `触发时机` 再做语义判断。

## 可选列边界

### AudioEvent 覆盖列

在默认映射不够时添加：

```text
总线
播放模式
是否循环
音量
音调
淡入秒数
淡出秒数
最大实例数
优先级
空间混合
最小距离
最大距离
衰减模式
```

### Switch 变体列

需要同一源事件根据 Switch 条件切到不同变体时添加：

```text
Switch源事件名
Switch条件
Switch优先级
```

`Switch条件` 使用分号分隔多条件：

```text
surface=grass;carry=stone
```

### State 列

需要进入某个 State 时播放事件时添加：

```text
State组
State值
State停止上一事件
State淡出秒数
```

### Parameter/RTPC 列

需要参数映射音量、音调或滤波时添加：

```text
参数名
参数作用目标
参数总线
参数事件名
参数输入最小值
参数输入最大值
参数输出最小值
参数输出最大值
```

只要写了 `参数名`，就必须同时保留 `参数事件名` 列。`参数事件名` 留空表示作用到总线；不要省略这一列，否则配置落地阶段会报错，避免把总线级参数误绑到当前事件。

## 推荐流程

新人或第一次跑真实需求时,优先按 `references/first-run-workflow.md` 的「从 0 开始的严格顺序」执行;下面是给熟练执行人的压缩版命令流程。

1. 确认 `sheetName`。没有则询问, 禁止默认 sheet。
2. 读取 `.gdconfig_tmp/xml/audio.xml`（X15）或 K1 配表上下文，以及 `references/demand-splitting.md`、`references/naming-and-reuse.md`；**K1 项目额外读取** `references/k1-audio-library.md` 并完成复用检查。
3. 从原始策划文档拆出可听触发点, 先生成 demand JSON; 不拆纯配置字段。
4. 对每行确定 Event/Asset、`新增/复用/沿用X1`、Bank/模块、优先级、Loop/StopEvent、描述和 Prompt。若是未来通用资源但当前尚不存在,必须标 `新增`,不要标 `复用`。
5. 运行 `build_production_package.py`, 默认产出 `audio_demand.xlsx`、`audio_sheet.xlsx`、master、公司库计划、AI 阻塞队列和所有必产模板。
6. 运行 `validate_production_package.py --stage prepared`; 未通过则不进入策划审核。
7. 把 `audio_demand.xlsx`、`planner_demand_review.xlsx` 和 `planner_demand_review.md` 发给策划/音频负责人,检查触发点、复用/新增、命名、优先级、Loop/StopEvent、Prompt 方向。
8. 策划确认后,将 `planner_demand_review.json` 的 `status` 改为 `approved`,并填写 reviewer/approvedAt/notes。未确认时不得运行公司库检索。
9. 运行 `run_company_library_search_plan.py`; 只搜索资产级新增项, 复用项不进搜索工作量。
10. 运行 `download_company_library_previews.py`, 优先下载短候选本地试听。
11. 先生成 review manifest, 再运行 `score_audio_feedback_preferences.py` 生成综合分。
12. 公司库 `candidate_count=0` 或 `qualified_candidate_count=0` 的新增资源必须进入 AI 补位。可用本地 `serve_review.py` 时,评审页点击 `AI生成候选` 应调用 `POST /api/ai-gap/generate` 生成并回填可播 WAV; 命令行批量模式则运行 `generate_ai_gap_queue.py --auto-approve-low-score`,默认生成 3 个候选。复用/沿用项禁止进 AI。
13. 重建评审页并传入 `--ai-manifest`; 公司库候选和 AI 候选必须在同一事件页面试听。若需要实时 AI 生成,构建评审页时显式加 `--enable-ai-api`,并启动 `serve_review.py`。
14. 运行 `validate_review_page_contract.py` 和 `validate_production_package.py --stage review-ready`, 必须检查候选数、可播数、低分缺口的 3 个 AI 候选、复用保护和导出控件。
15. 策划试听完成后点击页面的「提交判断并生成交付包」。本地服务先保存 decisions JSON, 再自动应用候选、整理 WAV、转 OGG 并运行 `handoff-ready` 校验。
16. 选择不完整、「改后用」尚未处理、「不合适」或缺失 OGG 时, 页面必须显示阻塞清单, 不得宣布交付成功。「导出判断」仅作为高级备份。
17. 需要人工追加 AI 时, 只对 `approved_for_ai` 运行 `generate_ai_gap_queue.py`; 默认仍生成 3 个 full/non-combined WAV 候选。
18. 策划选定候选后复制为 `wav/<音效资源名>.wav`, 再运行 `convert_wav_to_ogg.py`。已存在的复用 OGG 直接跳过。
19. 运行 `validate_production_package.py --stage handoff-ready`; 任何未决策、未解决 AI 队列、缺 OGG 或未验证复用都不能交付。
20. 通过后再告知用户运行 `audio-config-pipeline` 进行 XCfg 和 DisplayKey 闭环。

## Bundled 生产命令

以工作区根目录为当前目录, 以下命令中 `<sheetName>` 必须替换为用户指定的真实 sheet。

生成需求表、配置意图和生产包:

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/build_production_package.py `
  --demand-json "<demand.json>" `
  --sheet-name "<sheetName>" `
  --source "<source doc path>"
```

准备阶段验证:

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/validate_production_package.py `
  --sheet-name "<sheetName>" --stage prepared
```

策划审核闸口:

```text
1. 打开 .gdconfig_tmp/output/audio/production/<sheetName>/audio_demand.xlsx
2. 对照 .gdconfig_tmp/output/audio/production/<sheetName>/planner_demand_review.xlsx 或 planner_demand_review.md 检查拆分结果
3. 确认无误后,把 planner_demand_review.json 里的 status 改为 approved
```

公司库搜索与短候选下载:

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/run_company_library_search_plan.py `
  ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_search_plan.csv" `
  --output-json ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_search_results.json" `
  --output-csv ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_candidates.csv"

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/download_company_library_previews.py `
  ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_candidates.csv" `
  --output-dir ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_previews" `
  --manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_preview_map.json" `
  --config-dir ".gdconfig_tmp/.agents/skills/audio-production-pipeline"
```

生成评审页(默认不自动 AI):

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/build_company_library_review_page.py `
  --master ".gdconfig_tmp/output/audio/production/<sheetName>/audio_demand_master.csv" `
  --candidates ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_candidates.csv" `
  --preview-map ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_preview_map.json" `
  --manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review_manifest.json" `
  --output ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review.html" `
  --state-key "x15-audio-review-<sheetName>"

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/score_audio_feedback_preferences.py `
  --manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review_manifest.json" `
  --feedback ".gdconfig_tmp/output/audio/production/<sheetName>/planner_feedback.csv" `
  --output-manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review_scored_manifest.json" `
  --output-csv ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_scored_candidates.csv" `
  --profiles ".gdconfig_tmp/output/audio/production/<sheetName>/audio_preference_profiles.json"

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/generate_ai_gap_queue.py `
  --sheet-name "<sheetName>" `
  --review-manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review_manifest.json" `
  --auto-approve-low-score `
  --variants 3

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/build_company_library_review_page.py `
  --master ".gdconfig_tmp/output/audio/production/<sheetName>/audio_demand_master.csv" `
  --candidates ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_candidates.csv" `
  --preview-map ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_preview_map.json" `
  --manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review_manifest.json" `
  --scored-manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review_scored_manifest.json" `
  --ai-manifest ".gdconfig_tmp/output/audio/production/<sheetName>/ai_candidate_manifest.json" `
  --output ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review.html" `
  --state-key "x15-audio-review-<sheetName>" `
  --enable-ai-api

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/validate_review_page_contract.py `
  ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review.html"
```

服务评审页:

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/serve_review.py --port 8791
```

`serve_review.py` 同时提供 `POST /api/ai-gap/generate`、`GET /api/ai-gap/status/<jobId>` 和 `POST /api/production-package/build`。一键 AI 生成和一键交付都调用这个服务; 不要用普通 `http.server`, 否则只能试听而无法提交或生成。

导出决策后应用公司库选择和 AI 缺口:

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/apply_planner_decisions.py `
  --sheet-name "<sheetName>" --decisions "<planner-decisions.json>"

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/generate_ai_gap_queue.py `
  --sheet-name "<sheetName>" --variants 3
```

## 公司生成服务 Token

公司库检索和 AI 音效生成依赖公司音频服务。Token 不从 `company_library_review.html` 或 Git 仓库读取，也不能写进提交里。

OpenClaw 平台会自动注入 `TAPPER_AUTH_TOKEN` 环境变量，无需额外配置。Claude Code、Codex 或其他外部环境首次使用时，优先使用公司 TTS 服务的 `api_key`。

无 token 时不要继续调用接口。先把下面链接发给用户，让用户用公司账号登录后复制页面显示的 `api_key`：

```text
https://voiceclone.tap4fun.com/auth/apikey-login
```

用户贴回 `tts_xxxxx` 形式的 `api_key` 后，运行：

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/set_api_key.py <api_key>
```

它会写入本 skill 根目录的私有 `config.json`：

```json
{
  "api_key": "<paste_tts_api_key_after_login>",
  "jwt_token": "",
  "tapper_auth_token": ""
}
```

老用户仍可继续使用 `jwt_token` 或 `tapper_auth_token`。仓库提供 `config.example.json` 作为模板；真实 `config.json` 已被 `.gitignore` 忽略，不要提交。

生成服务读取顺序必须是：

1. 环境变量 `TAPPER_AUTH_TOKEN`
2. 本 skill 根目录私有 `config.json` 里的 `api_key`
3. 本 skill 根目录私有 `config.json` 里的 `jwt_token`
4. 本 skill 根目录私有 `config.json` 里的 `tapper_auth_token`

如果 token 缺失或过期，试听页仍能打开，但 `生成AI候选` / `生成全部AI缺口` 应显示明确的认证失败或生成服务失败状态，不能表现为无限排队。不要把 token、cookie、个人认证信息写入 `SKILL.md`、HTML、manifest、CSV、commit 或截图。

公司配置指南：

```text
https://skillsmp.tap4fun.com/skills/bi/tts-voice-generation
```

## WAV 转 OGG

AI 生成或音频生产端可以输出 WAV，但配置落地阶段只消费 `audio/<音效资源名>.ogg`。写完 `audio_sheet.xlsx` 后，先把本 sheet 的 WAV 转码到音频源仓：

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/convert_wav_to_ogg.py `
  --sheet-name "<sheetName>"
```

默认输入目录：

```text
.gdconfig_tmp/output/audio/production/<sheetName>/wav/<音效资源名>.wav
```

默认输出目录：

```text
audio/<音效资源名>.ogg
```

约定：

- WAV 文件名必须等于 `audio_sheet.xlsx` 里的 `音效资源名`，不含扩展名。
- 转码依赖本机 `ffmpeg`；如果机器没有 ffmpeg，脚本会失败并说明原因。
- 已存在的 OGG 默认不覆盖；需要重做时显式加 `--overwrite`。
- 只想检查缺哪些 WAV 时，加 `--dry-run`。

## Workbook 工具

优先使用 bundled 脚本，避免依赖 Excel COM 或第三方 Python 包。

创建或确保 sheet 存在：

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/audio_sheet_workbook.py ensure-sheet `
  --workbook .gdconfig_tmp/output/audio/audio_sheet.xlsx `
  --sheet-name "<sheetName>"
```

批量写入行时，把行数组保存成 JSON 后执行：

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/audio_sheet_workbook.py upsert-rows `
  --workbook .gdconfig_tmp/output/audio/audio_sheet.xlsx `
  --sheet-name "<sheetName>" `
  --rows-json "<rows.json>"
```

读取指定 sheet：

```powershell
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/audio_sheet_workbook.py read-sheet `
  --workbook .gdconfig_tmp/output/audio/audio_sheet.xlsx `
  --sheet-name "<sheetName>" `
  --json
```

## 完成标准

- 已处理指定 `sheetName`。
- `audio_demand.xlsx` 已落盘, 含生产状态、优先级、Prompt、Loop/StopEvent 和验收列。
- `planner_demand_review.md` 和 `planner_demand_review.json` 已落盘。进入公司库/AI 前,`planner_demand_review.json.status` 必须为 `approved`。
- `audio_sheet.xlsx` 中该 sheet 已完整表达本轮音效配置意图。
- `audio_sheet.xlsx` 保留 `生产状态` 和 `资源状态`,能区分已有复用与本轮新做后复用。
- 所有 `复用/沿用X1` 都必须已验证真实来源; `reuse_unverified` 不能进入后续公司库/AI/交付流程。需要本轮新做的通用资源必须作为 `新增` 进入生产。
- `.gdconfig_tmp/output/audio/production/<sheetName>/` 下的全部必产文件已存在(无候选时也要有空模板/占位结构),`wav/` 子目录已建立。
- 不能只因为文件存在就宣布完成; 必须运行 `validate_production_package.py` 的对应阶段。
- `review-ready` 要求新增资源有公司库候选或明确无候选状态, 并且页面有本地可播候选。
- 公司库无候选或 0 个合格候选的新增资源必须自动补 3 个 AI 候选; 复用/沿用资源禁止 AI。
- AI 候选生成在命令行阶段显式执行; 页面打开时不重复请求生成 API。
- `handoff-ready` 要求所有新增资源已决策, AI 队列无未解决行, 且每个 asset 都有最终 OGG 或已验证复用记录。
- 页面必须有「提交判断并生成交付包」; 成功后直接显示 `audio_sheet.xlsx`、`audio/` 和 `final_package_manifest.json` 路径。
- 如果存在 WAV 交付，已转成 `audio/<音效资源名>.ogg`，或已经在 `summary.md` 明确列出缺失原因。
- 不能由固定规则推导的信息已经写入可选列。
- 没有把"需要 AI 判断的信息"留给 `audio-config-pipeline`。
- 后续 `audio-config-pipeline` 可以只读这个 sheet 生成正式配置和 DisplayKey manifest。

## 相关资源

| 资源 | 用途 |
|------|------|
| `references/demand-splitting.md` | 从策划文档拆需求的 schema 与审核边界 |
| `references/first-run-workflow.md` | 第一次使用的严格步骤、闸门和常见误判 |
| `references/naming-and-reuse.md` | 命名与复用规则 |
| `references/review-page-contract.md` | 试听评审页稳定交互契约 |
| `references/review-page.md` | 公司库试听/选型辅助说明 |
| `references/prompt-profiles.md` | AI 生成音频提示词风格 |
| `references/repo-paths.md` | 生产端辅助产物目录约定 |
| `references/config-handoff.md` | 交付给配置落地阶段的契约 |
| `scripts/audio_sheet_workbook.py` | 维护本地 workbook |
| `scripts/generate_audio_demand_workbook.py` | 生成策划/音频可审核的 audio_demand.xlsx |
| `scripts/build_production_package.py` | 从 demand JSON 确定性生成配置意图和必产包 |
| `scripts/run_company_library_search_plan.py` | 运行公司库检索计划 |
| `scripts/download_company_library_previews.py` | 下载短候选到本地试听 |
| `scripts/build_company_library_review_page.py` | 生成 planner-first 公司库评审页 |
| `scripts/score_audio_feedback_preferences.py` | 候选质量/偏好/综合分 |
| `scripts/apply_planner_decisions.py` | 应用导出决策并准备最终 WAV / AI 缺口 |
| `scripts/generate_ai_gap_queue.py` | 仅生成经策划批准的 AI 缺口 |
| `scripts/validate_production_package.py` | prepared/review-ready/handoff-ready 内容级验证 |
| `scripts/serve_review.py` | 本地评审服务,支持 AI 生成状态和一键交付 |
| `scripts/convert_wav_to_ogg.py` | 按 audio_sheet 指定 sheet 把 WAV 转成 audio 仓 OGG |
