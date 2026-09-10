# K1 独立音效需求

只生成 K1 需求 JSON 和 `audio_demand.xlsx`；不调用 `build_production_package.py`，不修改 `audio_sheet.xlsx`，不创建候选、试听或 AI 生产包。不要求 X15 工作区或生产 sheetName。

## 拆分与生成

1. 读取主案及已有界面／表现资料，按 `k1-audio-library.md` 和 `.json` 核对复用来源。只拆有依据的玩家可听触发点，不把后端字段拆成音效。
2. 按 `demand-splitting.md` 的 JSON 外形写 `project: K1` 和 `sheets`；需求页名称沿用功能简称，属于本地展示名称，可直接确定。每条真实需求填写 `event`（业务触发标识，拟定名称注明拟定）、`tag`、`asset`、`trigger`、`priority`、`loop` 和 `stop_event_needed`。K1 不要求 X15 Bank、接口命名或 OGG 路径。
3. 新增声音填写 `desc`，`asset` 可用明确标注的拟定资源名；Prompt、公司库关键词在进入生产时再补，不作为需求完成条件。复用可使用已核实 AudioList ID 或文件名，并在 `notes` 写可定位来源与核验依据。循环音效必须声明 `stop_event_needed: TRUE` 并填写 `stop_condition`，说明具体何时停止。
4. 每个 sheet 的 `note` 写来源及本次核查结论。确实没有音效触发需求时，`rows: []`，在 note 说明核查范围与依据，不添加假需求行；有复用触发点则保留复用行。
5. 运行 `python <本Skill>/scripts/generate_audio_demand_workbook.py <输出xlsx> <需求json>`。建议输出 `output/<功能名>-音效需求/`，生成器在写文件前验证 K1 必填信息、重复事件、零需求依据、复用依据和循环停止条件。

## 验收与停止点

逐项对照来源核验触发覆盖、复用真实性和停止条件；脚本只能验证字段存在，不能替代来源核验。回读 Excel 检查行数、触发、资源、备注与停止条件均保留，且没有 X15 专用说明。

上述通过表示“需求文档已生成，待策划审核”；不等同于需求已批准、声音已制作或可交付客户端。不因等待后续生产审核而把已经完成的需求文件标成生成失败。确实缺影响需求正确性的输入时报告部分完成。

本模式不运行 `validate_production_package.py`。后续明确进入生产时重新核对工程命名、工作区、sheetName 和制作范围，不将本地拟定标识当作已存在的工程资源。
