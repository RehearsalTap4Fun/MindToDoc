# Config Handoff

`audio-production-pipeline` 的最终配置交接文件是配置意图表：

```text
<workspaceRoot>/.gdconfig_tmp/output/audio/audio_sheet.xlsx
```

用户指定的 `sheetName` 是该 workbook 里的真实工作表名。`audio-config-pipeline` 会读取同一个 workbook 和同一个 `sheetName`，按固定规则展开成正式 XCfg 音频配置、Unity manifest 和 DisplayKey 回填。

`audio_sheet.xlsx` 不是原始需求表，也不是正式配置表。它必须已经完成 AI 语义推断，表达完整配置意图。

## Production 阶段负责

- 理解需求。
- 决定 `事件名`、`音效资源名`、`功能模块`、`声音类型`、`描述`、`触发时机`。
- 在需求需要时新增 Switch、State、Parameter 或 AudioEvent 覆盖列。
- 只写必要可选列，不铺满所有正式配置列。
- 输出音频端需要的试听页、AI 缺口、制作交付或最终包。
- 如果音频端交付 WAV，先按 `音效资源名` 转成 `audio/<音效资源名>.ogg`。
- 确保 `audio_sheet.xlsx` 已经是标准配置意图结果。

## Config 阶段负责

- 按固定映射和显式列机械生成正式配置。
- 不从 `描述` 或 `触发时机` 做二次语义推断。
- 生成 Unity manifest。
- 配合 Unity 工具复制 `.ogg` 到 Unity 资源目录。
- 配合 Unity 工具生成 DisplayKey。
- 回填 `AudioEvent.资源DisplayKey`。

音频资源交接边界：

- `audio-production-pipeline` 可以产出 WAV，但必须在交接前用 `scripts/convert_wav_to_ogg.py` 转成 OGG。
- `audio-config-pipeline` 只消费 `audio/<音效资源名>.ogg`，不负责 WAV 转码。

## CSV 边界

不要再把这些旧文件作为 `audio-config-pipeline` 的主输入源：

```text
AudioEvent_Config.csv
DisplayKey_Sheet.csv
Program_Integration_Manifest.csv
```

配置落地主流程只消费 `audio_sheet.xlsx`。如果音频端、策划验收或人工交接需要 CSV,可以从 `audio_sheet.xlsx` 的指定工作表、评审决策 JSON 或最终 manifest 派生,但不要让 `audio-config-pipeline` 反过来读取这些 CSV。

## Final Checks

- 用户已明确指定 `sheetName`。
- 指定 sheet 中每一行都是一个完整配置意图。
- 基础列齐全。
- 需求中不能由固定映射推导的信息已经落成可选列。
- 需要 AI 判断的信息没有留给 config 阶段。
- 多事件复用同一个声音时，`音效资源名` 完全相同。
- 如果本轮有 WAV 交付，对应 `audio/<音效资源名>.ogg` 已生成或已明确缺失原因。
