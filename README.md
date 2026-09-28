# MindToDoc

MindToDoc 把脑图、框架文档、参考游戏或既有开发文档，整理为可评审的移动游戏功能策划案，并按真实需求生成配置表结构、界面标注等派生文档。

项目主要以 Codex Skill 方式使用。根目录 [SKILL.md](SKILL.md) 定义工作流和判断分流，细则集中在 [references/](references/)；README 负责快速上手和项目导航。

## 核心能力

- 扫描 [input/](input/) 或指定文件，识别脑图、Markdown、Excel 和迁移源。
- 逐模块澄清功能定位、参考玩法、关键决策、异常边界与数据兼容，并主动指出规则缺口。
- 先判定小型需求或完整功能案，再按唯一的[派生流程](references/derived-documents-workflow.md)确定交付。小型需求默认一份主案；完整功能案核查并交付配置结构、BI、美术、音效，其他派生按条件生成。
- 在起草和精简时检查范围、归属、重复内容与唯一真相源，避免空章节、空派生物和过度设计。
- 用户提供截图后完成界面识图、编号、审核和左图右文标注。
- 按需把本地 Markdown 同步到钉钉；本地文件始终是内容 SSOT。

## 快速开始

1. 把脑图、框架文档、参考资料或既有 `*-开发文档.md` 放入 [input/](input/)，也可以在请求中直接指定文件。
2. 在 Codex 中触发 `mindtodoc`，例如：

   ```text
   使用 mindtodoc，读取 input/ 中的素材，先逐项澄清规则，再生成主功能案和确有依据的派生文档。
   ```

3. 逐项确认功能定位、参考玩法、关键决策、模块范围和计划交付物；信息不足时先决策，不直接臆造正文。
4. 审核 [output/](output/) 中的主案和按需派生文档，确认结论后再继续下一模块或修订。
5. 有截图时再走界面标注流程；需要在线协作时再同步钉钉。
6. 项目完成后，把完整产物归档到 `examples/<项目名>/`，供后续项目参考。

## 产物与边界

当前批次仅维护冷库服与秘宝业务文档，其他已完成开发的文档保留历史状态；详见[本次维护范围](deliveries/README.md)。

| 产物 | 默认路径 | 职责 |
|---|---|---|
| 主功能案 | `output/<功能名>.md` | 变更记录、简介、关键决策、详细规则、边界情况与数据兼容 |
| 配置表结构 | `output/<功能名>-配置表结构.md` | 数值策划 Excel 的表、页签和字段，以及公共配置依赖 |
| 界面标注 | `output/<功能名>-界面标注.md` | 截图编号、控件表现、红点、多语言 key 和左图右文说明 |
| 界面素材 | `output/ui-annotation/assets/` | 原图、标注图及标注数据 |
| 其他派生 | 见[派生流程](references/derived-documents-workflow.md) | 完整功能案固定的 BI、美术、音效；经确认的 Checklist、测试用例 |
| 旧版迁移源 | `output/<游戏名>-开发文档.md` | 只读基础材料；新稿不覆盖原文件 |

内容归属速记：

- 玩法异常、重复请求、活动结束、断线和数据兼容怎么处理，写在**主功能案**。
- 数值策划在 Excel 中填写哪些表和字段，写在**配置表结构派生文档**。
- 按钮、布局、文案 key、红点和截图编号，写在**界面标注派生文档**。

## 工作流程

1. **读取输入**：扫描 `input/`、用户指定文件和已有迁移源；无素材时停止，不硬生成。
2. **确认整体框架**：确认功能定位、参考玩法、关键决策、模块范围和最小交付物。
3. **逐模块深入**：补全触发条件、状态分支、不满足提示、结果反馈、边界情况与数据兼容。
4. **按需生成派生文档**：已有同用途材料优先复用；没有事实依据时不创建空文档。
5. **界面标注**：仅在用户提供截图后进行识图、红圈编号、审核和左图右文落稿。
6. **钉钉同步**：需要在线协作时，先更新本地 Markdown，再转换并同步。
7. **项目归档**：完成后把输入、输出和项目专属工具整理到 `examples/<项目名>/`。

## 目录结构

| 路径 | 用途 |
|---|---|
| [SKILL.md](SKILL.md) | Skill 主流程、写作判断和跨 reference 分流 |
| [templates/](templates/) | 主案、模块章、配置表结构和界面标注模板 |
| [references/](references/) | 主案边界、写作规则、手游专项、精简审查、K1 公共配置、界面与钉钉细则 |
| [scripts/](scripts/) | 钉钉转换、反转义、补表计划和静态检查工具 |
| [input/](input/) | 当前任务的原始素材；内容随项目变化 |
| [output/](output/) | 当前任务的主案、派生文档和中间产物；内容随项目变化 |
| [examples/](examples/) | 已完成项目的稳定归档，供参考，不作为当前任务编辑区 |
| [deliveries/](deliveries/) | 当前功能交付登记、源稿与派生指纹、待处理事项 |
| [tests/fixtures/](tests/fixtures/) | 可重复验证的格式样例 |
| `.codex_tmp/` | 本地临时报告和中间文件，不提交 |
| [docs/superpowers/](docs/superpowers/) | 设计与实施计划记录；运行规则仍以根目录 `SKILL.md` 为准 |

## 关键原则

- **本地 Markdown 是 SSOT**：钉钉等在线文档按需同步，不反向取代本地定稿。
- **一个完整功能一份主案**：子模块不拆成多份独立策划案；配置、界面和专项需求按职责派生。
- **按模式交付且有事实依据**：小型需求使用[单文档模板](templates/small-requirement.md)。完整功能案使用[主案模板](templates/doc-structure.md)，无新增的固定派生保留简短核查结论及复用依据，不虚构需求；界面标注、Checklist、测试用例按派生流程的条件生成。
- **详细规则只有一个落点**：关键决策保留摘要，完整条件与分支集中在唯一 SSOT，其他位置引用或复用。
- **精简不等于删规则**：边界情况、数据兼容、核心机制和设计意图属于保护项，不为追求字数目标而删除。
- **用户决策先于落稿**：未明确的选择逐项确认；只有用户明确未定的内容才能标为待确认。

## 规则导航

- [SKILL.md](SKILL.md)：完整工作流、产出位置、阶段分流和自检清单。
- [主功能案内容边界](references/feature-spec-boundaries.md)：主案写什么、不写什么，以及数值和奖励粒度。
- [功能案写作规则](references/feature-spec-writing.md)：起草顺序、功能与界面归属、多级列表和成稿清理。
- [策划精简判断梯](references/spec-minimalism-ladder.md)：范围收口、重复处理、迁移闭环、保护项和审查输出契约。
- [手游系统规则](references/mobile-system-rules-reference.md)：流程图、红点、线上兼容、配置边界和 K1 关键常量。
- [K1 公共配置表](references/k1-common-configs.md)：活动、通行证、排行、礼包、邮件、联盟和 KVK 等公共依赖。
- [界面标注规范](references/ui-annotation-reference.md)：识图、归类、编号、审核、左图右文和 key 表。
- [钉钉同步规范](references/dingtalk-sync-reference.md)：Markdown/JSONML 转换、表格、图片和转义清洗。
- [审核三档纪律](references/audit-three-tier-discipline.md)：审核、检验和复核任务的硬范围、软分布与设计意图断言。

## 示例项目

- [2026 世界杯主题活动](examples/2026世界杯主题活动/)：主案、配置表、界面标注、关卡工具链、美术/音效需求和钉钉同步材料等完整产物。
- [K1 新服大地图重构](examples/K1新服大地图重构/)：K1 新服大地图重构的主案、配置表结构和界面标注等归档产物。

示例目录保存历史业务案例，不代表符合最新格式规范。当前任务在根目录的 `input/` 与 `output/` 中进行；可重复验证的最小样例见 `tests/fixtures/`。

## 依赖与辅助工具

Python 3.10+。依赖按能力区分，见[能力依赖说明](references/dependencies.md)；vendor 中包含专用流程，但部分查询和在线能力仍需要外部 Skill、工具或鉴权。

辅助脚本使用 Python。安装运行依赖：

```powershell
python -m pip install -r requirements.txt
```

需要运行仓库测试或开发校验时，再安装可选依赖：

```powershell
python -m pip install -r requirements-dev.txt
```

交付前按[质量与登记规范](references/delivery-quality.md)核验。以下命令只检查，不改写稿件：

```powershell
python scripts/doctor.py
python scripts/check_doc_quality.py tests/fixtures/small-requirement.md
python scripts/check_delivery.py deliveries/example-small.json
python -B -m pytest -q -p no:cacheprovider
```

实际交付时把示例路径替换为本次文件及登记。通过格式和指纹检查不能替代规则审核。
图片标注另装 `requirements-image.txt`。浏览器安全回归需 Node、Playwright 和 Chromium；设置 `AUDIO_REVIEW_NODE` 为 Node 可执行路径，`PLAYWRIGHT_MODULE` 为 Playwright 模块路径后运行 pytest，未配置时该项明确跳过。

| 工具 | 用途 |
|---|---|
| [md2jsonml.py](scripts/md2jsonml.py) | 把主案 Markdown 转为钉钉 JSONML，并生成表格、图片 sidecar 和大文档主体 |
| [dingtalk_md_unescape.py](scripts/dingtalk_md_unescape.py) | 清理钉钉导出 Markdown 的严格转义，也可检查残留转义 token |
| [dingtalk_table_inserter.py](scripts/dingtalk_table_inserter.py) | 根据文档块和表格 sidecar 生成补表执行计划，不直接调用钉钉 API |
| [list_tbd.py](scripts/list_tbd.py) | 扫描 Markdown 中的 TBD，输出数量、位置和阈值告警 |
| [check_doc_quality.py](scripts/check_doc_quality.py) | 显式文件的格式、占位符与本地资源检查 |
| [check_delivery.py](scripts/check_delivery.py) | 交付范围、审核状态和内容指纹检查 |
| [doctor.py](scripts/doctor.py) | 按能力检查本地依赖 |
| [check_plan_signatures.py](scripts/check_plan_signatures.py) | 检查实施计划内 Python 代码块语法和关键符号一致性 |

## 维护与协作

- 开展新工作前检查 Git 状态；仅在工作区干净且需要同步时运行 `git pull --ff-only`。提交时只包含本次改动，保留未提交的其他工作。
- 修改工作流时更新 [SKILL.md](SKILL.md) 或对应 reference；README 只同步入口信息和导航，不复制长规则。
- 审核、检验或复核类任务先按[审核三档纪律](references/audit-three-tier-discipline.md)确定断言层级，再修改产物。
- 项目专属工具和材料随项目一起归档到 `examples/<项目名>/`；可复用规则和工具才保留在根目录。
