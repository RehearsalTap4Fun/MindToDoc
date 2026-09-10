# First Run Workflow

K1 仅生成需求文档时先走 `k1-demand-only.md` 并在需求交付后返回；以下工作区、sheetName、生产包及审核闸门用于完整生产流程。

本页给第一次使用 `audio-production-pipeline` 的策划、音频或配置同学看。目标是防止把所有脚本随便跑一遍,而是按闸门顺序完成音效生产流程。

## 一句话流程

```text
先拆需求并审核 -> 再配置 API -> 再搜索/生成候选 -> 再试听决策 -> 最后交付 OGG 和配置意图
```

## 角色分工

| 角色 | 主要动作 |
|---|---|
| 策划 | 提供功能文档,审核 `audio_demand.xlsx` 里是否漏拆、多拆、错拆。 |
| 音频 | 审核新增声音方向、候选质量、是否需要 AI 补位或修改。 |
| 工具执行人 | 按步骤运行脚本,不跳过闸门,记录失败原因。 |
| 配置/程序 | 在 handoff-ready 后消费 `audio_sheet.xlsx` 和 `audio/` 资源。 |

## 从 0 开始的严格顺序

### 0. 确认工作区和 sheetName

必须在同时包含 `.gdconfig_tmp`、`audio`、`client` 的工作区根目录运行。必须指定 `sheetName`。没有 sheetName 时先问清楚,不要默认 `Sheet1`。

### 1. 从功能文档拆需求

先把策划文档拆成 demand JSON,再运行 `build_production_package.py`。这一阶段只回答:

- 哪些玩家可听触发点需要声音。
- 每条声音的事件名、资源名、触发时机、优先级。
- 哪些是真实复用,哪些必须新增。

不能直接跳到公司库、AI、试听页或正式配置。

### 2. 生成并校验 prepared 包

运行:

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/build_production_package.py \
  --demand-json "<demand.json>" \
  --sheet-name "<sheetName>" \
  --source "<source doc path>"

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/validate_production_package.py \
  --sheet-name "<sheetName>" --stage prepared
```

prepared 阶段只允许 1 个常见 warning: `planner demand review is pending`。如果有 error,先修需求表或工具问题,不要继续往下跑。

### 3. 策划/音频审核需求表

把这些文件给策划或音频负责人看:

```text
.gdconfig_tmp/output/audio/production/<sheetName>/audio_demand.xlsx
.gdconfig_tmp/output/audio/production/<sheetName>/planner_demand_review.xlsx
.gdconfig_tmp/output/audio/production/<sheetName>/planner_demand_review.md
```

审核重点:

- 有没有漏掉玩家能听到的关键触发点。
- 有没有把纯配置字段、概率、文本 key 拆成声音。
- `新增/复用/沿用X1` 是否正确。
- Loop 行是否需要 StopEvent。
- 新增声音的描述和 prompt 是否符合功能表现。

### 4. 通过审核闸门

只有需求审核通过后,才能把:

```text
.gdconfig_tmp/output/audio/production/<sheetName>/planner_demand_review.json
```

里的 `status` 从 `pending_planner_review` 改成 `approved`,并填写 reviewer、approvedAt、notes。未 approved 时公司库检索脚本会阻断,这是正确行为。

### 5. 配置公司音频 API

公司库检索、候选下载和 AI 生成需要 token 或 api_key。没有凭证时只能停在 prepared 或 dry-run,不能得到真实候选。

首次配置用:

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/set_api_key.py <tts_api_key>
```

真实 key 只允许写入本 skill 私有 `config.json`,不要写进 HTML、CSV、manifest、需求表或 git。

### 6. 跑公司库搜索和预览下载

只对 `新增` 资产跑公司库搜索。`复用/沿用X1` 不进入搜索和 AI 工作量。

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/run_company_library_search_plan.py \
  ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_search_plan.csv" \
  --output-json ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_search_results.json" \
  --output-csv ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_candidates.csv"

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/download_company_library_previews.py \
  ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_candidates.csv" \
  --output-dir ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_previews" \
  --manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_preview_map.json" \
  --config-dir ".gdconfig_tmp/.agents/skills/audio-production-pipeline"
```

### 7. 生成正式评审页

`build_production_package.py` 生成的 `company_library_review.html` 只是 prepared 占位页,不能当正式试听页。搜索/下载后必须用正式评审页生成器重建。

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/build_company_library_review_page.py \
  --master ".gdconfig_tmp/output/audio/production/<sheetName>/audio_demand_master.csv" \
  --candidates ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_candidates.csv" \
  --preview-map ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_preview_map.json" \
  --manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review_manifest.json" \
  --output ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review.html" \
  --state-key "x15-audio-review-<sheetName>" \
  --enable-ai-api
```

### 8. 生成低分/无候选 AI 补位

公司库无候选或没有合格候选的新增资源,必须补 3 个 AI 候选。复用资源禁止 AI。

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/generate_ai_gap_queue.py \
  --sheet-name "<sheetName>" \
  --review-manifest ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review_manifest.json" \
  --auto-approve-low-score \
  --variants 3
```

生成后用 `--ai-manifest` 重建评审页。

### 9. 验证 review-ready

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/validate_review_page_contract.py \
  ".gdconfig_tmp/output/audio/production/<sheetName>/company_library_review.html"

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/validate_production_package.py \
  --sheet-name "<sheetName>" --stage review-ready
```

只有 `errors=0 warnings=0` 时,才把页面发给策划试听。

### 10. 策划试听并提交决策

启动本地服务:

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/serve_review.py --port 8791
```

打开评审页后,策划逐条选择直接用、改后用或不合适。页面里的“提交判断并生成交付包”会保存决策并尝试整理交付。

不要用普通 `http.server` 代替 `serve_review.py`;普通静态服务不能调用 AI 生成或一键交付 API。

### 11. 应用决策、转 OGG、校验 handoff-ready

如果没有通过页面一键交付,可以命令行应用决策:

```bash
python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/apply_planner_decisions.py \
  --sheet-name "<sheetName>" --decisions "<planner-decisions.json>"

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/convert_wav_to_ogg.py \
  --sheet-name "<sheetName>"

python .gdconfig_tmp/.agents/skills/audio-production-pipeline/scripts/validate_production_package.py \
  --sheet-name "<sheetName>" --stage handoff-ready
```

handoff-ready 必须没有未决策新增资源、未解决 AI 队列、缺失 OGG 或未验证复用。

## 不能跳过的闸门

| 闸门 | 没过时不能做什么 |
|---|---|
| prepared error 未清零 | 不能进入公司库/AI/试听。 |
| `planner_demand_review.json.status != approved` | 不能公司库检索或 AI 生成。 |
| 没有 api_key/token | 不能真实搜索公司库、下载候选或生成 AI。 |
| 没有公司库候选/AI 候选 | 不能宣称 review-ready。 |
| 没有策划试听决策 | 不能宣称 handoff-ready。 |
| 没有最终 `audio/<asset>.ogg` | 不能交付配置落地。 |

## 复用硬规则

`复用` 不是“这个声音很通用”。`复用` 只能表示当前工作区已经有真实文件:

```text
audio/<音效资源名>.ogg
```

如果文件不存在,即使资源名是 `common_btn_click`、`common_chest_click` 这类通用名,也必须标 `新增`。本轮新建的通用资源要等转成 OGG 并通过 handoff-ready 后,后续需求才允许复用。

## 常见误判

| 现象 | 判断 |
|---|---|
| `planner demand review is pending` | 正常闸门,不是工具坏。 |
| 没 token 导致公司库/AI 阻断 | 环境未配置,不是需求拆分失败。 |
| review-ready 报没有候选 | 没跑公司库下载或 AI 补位,流程没到位。 |
| dry-run 规划了 WAV 但 handoff 缺 OGG | dry-run 不会生成真实音频。 |
| 初始 `company_library_review.html` 不能试听 | prepared 占位页,需要正式重建。 |
| 系统 Python 缺 `openpyxl` | 使用 bundled Python 或安装依赖。 |
