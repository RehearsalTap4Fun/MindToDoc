# 交付质量与版本核验

本文件承接联合检查的执行入口，不重新定义交付类型。类型和触发条件以 `derived-documents-workflow.md` 为准。

## 三步验收

1. **机械检查**：`python scripts/check_doc_quality.py <本次主案.md>`。检查格式、模板残留和本地文件链接。不请求远端，也不验证章节片段锚点，行内代码不参与检查。
   - 新稿与完整重整：不加参数，须零问题。
   - 局部修订：加 `--baseline <修订前的 git 版本>`，只报本次新增的问题，须清零。既存问题写进登记的 `known_issues`，不借修订重新生成整套业务文档。
2. **语义复核**：逐项检查本次受影响的主体、触发、条件、动作、成功/失败/取消/恢复与异常。业务规则只有一个完整定义位置，主案、界面文案、配置说明、日志与音效引用一致。机械脚本不能证明这一步通过。
3. **登记基线**：在 `deliveries/<功能标识>.json` 记录模式、主案路径及 SHA-256、每个派生的类型/路径/指纹/核验状态/依据。`reviewed` 表示已完成本次范围的核验；`pending` 表示待核验。执行 `python scripts/check_delivery.py deliveries/<功能标识>.json`，内容变化或未完成时非零退出。
   - 登记不手算指纹，逐个文件在复核完成后执行：
     - 主案：`python scripts/check_delivery.py deliveries/<功能标识>.json --record output/<功能>.md --source --feature <功能名> --mode complete`
     - 派生：`python scripts/check_delivery.py deliveries/<功能标识>.json --record <派生路径> --kind bi --status reviewed --note "<核验范围与规则落点>"`
   - `--record` 每次只改一个条目，其余条目的指纹保持不变。

登记路径相对于 JSON 所在目录。完整功能案至少包含 `config`、`bi`、`art`、`audio` 四类；小型需求无需凑齐派生。图片和其他产物可登记为 `image`、`ui` 等。缺失文件仍登记为 pending 并解释，不能删掉缺失项来让检查通过。

- 指纹通过只表示文件与审核时相同。
- 不得自动批量刷新指纹，也不得用脚本循环 `--record` 代替逐项复核。
- 更新源稿后，先重审受影响内容，再记录新指纹。
- `review_note` 写核验范围与具体规则落点，不能只写“检查通过”。

格式：顶层 `schema_version: 1`、`feature`、`mode: small|complete`、`source: {path, sha256}`、`artifacts: [{kind, path, sha256, status, review_note}]`。可附 `known_issues` 记录范围内尚未解决事项，非空时登记检查不得报告完整交付。

## 样例和目录

- `tests/fixtures/`：可重复运行的格式与转换样例，样例玩法仅用于测试。
- `examples/`：历史业务归档，查历史结论时读取，不直接当最新模板复制。
- `input/`、`output/`：保留现有路径。新功能可以使用各自的子目录，以登记文件明确主案、派生和素材，避免只靠文件名前缀推测状态。
- `docs/work/`：决策与审核记录；正式正文不承载工具执行过程。
- `.codex_tmp/`：转换、回读和测试临时文件，不作为正式来源，不入库。

归档或移动文件后，修复引用并重新检查，再更新登记。不要先搬动历史目录再尝试恢复链接。
