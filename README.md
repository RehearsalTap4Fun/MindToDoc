# MindToDoc

把 `input/` 中的脑图、框架文档或参考资料，整理为 **system-design-doc 格式**的功能策划案及派生文档。

## 目录

- `SKILL.md`：技能主流程（对齐 `system-design-doc` 定稿规范）
- `templates/`：主案、模块章、配置表派生、界面标注派生模板
- `input/`：原始素材
- `output/`：主功能案、`-配置表结构.md`、`-界面标注.md` 等
- `output/ui-annotation/assets/`：界面截图与红圈标注图
- `output/system-design-doc-samples/`：迁移样例（世界杯主题活动）
- `docs/superpowers/`：**已归档 (archived)** — 2026-06-01 旧版设计/计划，含已废弃 HTML 原型方案；以根目录 `SKILL.md` 为准

## 使用流程

1. 素材放入 `input/`（或指定既有 `*-开发文档.md` 作迁移源）。
2. 确认功能定位、模块清单、文档粒度（整功能一份主案）。
3. 逐模块写主案规则；配置表字段、界面标注写入派生 md。
4. 用户提供截图后，走界面标注标准流程（识图 → 红圈 → 审核 → 左图右文）。
5. 按需同步钉钉；本地 md 为 SSOT。

## 当前样例

- 旧版（只读素材）：`output/2026世界杯主题活动-开发文档.md`
- 定稿格式：`output/system-design-doc-samples/2026世界杯主题活动.md` 及配置表/界面标注派生

## 世界杯测试配置工具

首次运行先安装依赖:

```bash
python3 -m pip install -r requirements-dev.txt
```

常用命令:

```bash
python3 output/test-config/generate_activity_soccer_test_config.py
python3 output/test-config/level-tags/apply_level_tags.py
python3 scripts/check_protocol_drift.py
python3 scripts/check_preset_consistency.py
python3 scripts/check_xlsx_drift.py --summary
python3 -m pytest output/test-config/level-tags/tests -q
```

## 协作约定

每次开展新工作前先 `git pull --ff-only`；完成有效改动后提交。
