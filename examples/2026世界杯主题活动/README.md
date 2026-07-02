# 2026世界杯主题活动（示例项目存档）

本目录是用 mindtodoc 技能完成的一个示例项目的完整产物存档，供参考，不建议在此基础上继续修改（新需求另起 `input/`/`output/`）。

## 目录说明

- `input/`：原始素材（脑图、原型图、参考文档）
- `output/`：主案 `2026世界杯主题活动.md` 及配置表结构/界面标注等派生文档；`test-config/` 为配置生成工具链；`prototypes/` 为界面原型页；`dingtalk-sync/`、`dingtalk-source/` 为钉钉同步中间产物
- `docs/`：美术/音效需求、评审记录、生成音效资源
- `references/soccer-coordinate-protocol.md`：本项目专属的足球场地坐标系协议
- `scripts/`：本项目专属的校验/生成脚本，依赖上述坐标协议与 `output/test-config/` 下的生成器
- `.mmcheck/`：流程图 mermaid 校验产物

## 世界杯测试配置工具

首次运行先安装依赖（在仓库根目录执行）：

```bash
python3 -m pip install -r requirements-dev.txt
```

常用命令（在仓库根目录执行，路径含中文需加引号）：

```bash
python3 "examples/2026世界杯主题活动/output/test-config/generate_activity_soccer_test_config.py"
python3 "examples/2026世界杯主题活动/output/test-config/level-tags/apply_level_tags.py"
python3 "examples/2026世界杯主题活动/scripts/check_protocol_drift.py"
python3 "examples/2026世界杯主题活动/scripts/check_preset_consistency.py"
python3 "examples/2026世界杯主题活动/scripts/check_xlsx_drift.py" --summary
python3 -m pytest "examples/2026世界杯主题活动/output/test-config/level-tags/tests" -q
```
