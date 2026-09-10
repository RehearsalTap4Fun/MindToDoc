# 音频生产端辅助产物目录

本文件只约定 `audio-production-pipeline` 的辅助产物放置位置，不再记录任何个人机器绝对路径。

## 根目录

所有音频生产端辅助产物统一写到配置仓库内：

```text
.gdconfig_tmp/output/audio/production/<sheetName>/
```

这里的 `<sheetName>` 是用户指定的 workbook sheet 名。处理一个 sheet，就生成或复用一个同名目录。

如果 sheet 名包含 Windows 路径非法字符（`\ / : * ? " < > |`），目录名需要把非法字符替换成 `_`，并在目录内写入 `sheet.meta.json` 记录原始 sheetName，避免后续人工排查时对不上。

## 必产文件

每次跑 `audio-production-pipeline` 流程,目录下都必须默认创建以下全部文件。无内容时落空模板/占位结构,不能省略。目录不存在时直接创建,不要等用户主动要。

| 文件 | 必填内容 / 占位规则 |
|------|---------------------|
| `sheet.meta.json` | 原始 `sheetName`、安全目录名、生成时间 (`generatedAt`)、来源 (`source`)、行数。**始终必产**。 |
| `audio_demand.xlsx` | 策划/音频可审核的需求拆分表,含触发点、资产级复用、制作状态、Prompt 和验收列。**始终必产**。 |
| `planner_demand_review.xlsx` + `planner_demand_review.md` + `planner_demand_review.json` | 策划逐行审核表、文字审核清单与机器可读审核状态。`xlsx` 用来审核需求拆得准不准确;首次生成时 `status=pending_planner_review`; 公司库/AI 前必须改为 `approved`。**始终必产**。 |
| `audio_demand_master.csv` + `audio_sheet_rows.json` | 交给公司库/评审工具的结构化需求,以及写入 `audio_sheet.xlsx` 的确定性行数据。**始终必产**。 |
| `summary.md` | 已确定 / 待制作 / 待确认问题。**始终必产**;无待确认问题时写 `无待确认问题`。 |
| `sound_design.json` | 每个新资源的声学方向 (`acoustic`)、避免 (`avoid`)、`promptProfile`、时长偏好;复用资源标记 `reuse` 字段。**始终必产**。 |
| `company_library_search_plan.csv` | 每个资源一行,包含优先关键词、次级关键词、音长、品质、排除关键词;复用资源在 `备注` 列写「沿用X1」。**始终必产**;不走公司库时所有资源行的关键词列可留空,但行不能省。 |
| `company_library_search_results.json` + `company_library_candidates.csv` | 公司库原始搜索结果与扁平候选表。尚未搜索时保留空结构/表头。**始终必产**。 |
| `company_library_preview_map.json` + `company_library_previews/` | 已下载本地候选的映射与目录。尚未下载时保留空结构/空目录。**始终必产**。 |
| `company_library_review.html` + `company_library_review_manifest.json` | 评审页(含筛选/排序/导出)与对应 manifest;按 `references/review-page.md` 规则生成。**始终必产**;复用资源在 manifest 中标记 `reuse`,不进入主决策工作流。 |
| `ai_gap_queue.csv` | 每个新资源的 AI 生成 prompt(基于 `references/prompt-profiles.md`),含 avoid、duration、status、priority;复用资源不进入此文件。**始终必产**;若全部资源都是复用,文件保留表头 + 空数据行。 |
| `planner_decisions.json` | 评审决策导出文件;首次生成时为空模板(`decisions: []`),策划试听后由 `company_library_review.html` 导出覆盖。**始终必产**。 |
| `planner_feedback.csv` + `audio_preference_profiles.json` | 候选反馈与可复用偏好画像;首次为空表/空结构。**始终必产**。 |
| `decision_application_manifest.json` + `ai_candidate_manifest.json` | 决策应用与 AI 执行结果;未执行时保留 `pending` 占位。**始终必产**。 |
| `final_package_manifest.json` | 最终交付清单:复用资源列表、待制作 WAV/OGG 路径、状态、流转步骤。**始终必产**。 |
| `wav/` | 生产端 WAV 交付目录,文件名必须是 `<音效资源名>.wav`。**始终必产空目录**;实际 WAV 由音频生产端或 AI 生成阶段后续投放。 |

## 使用约定

- `audio_sheet.xlsx` 仍然固定在 `.gdconfig_tmp/output/audio/audio_sheet.xlsx`，它是配置落地阶段的唯一源数据。
- `production/<sheetName>/` 只是生产端辅助目录，不是正式配置源。
- 生产端可以交付 WAV，但进入配置落地前必须用 `scripts/convert_wav_to_ogg.py` 转成 `audio/<音效资源名>.ogg`。
- 不要把个人下载目录、Mac/Windows 绝对路径写入 skill 或产物清单。
- 如果需要引用外部音频仓库文件，只记录相对资源名、音效资源名或说明；真正的本机路径由执行人按当前机器环境自行提供。
