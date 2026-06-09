# MindToDoc

MindToDoc 是一个用于把早期游戏想法整理成专业开发文档的项目。当前形态是 Codex/Superpowers 风格的 `mindtodoc` 技能：读取 `input/` 中的脑图、框架文档或参考资料，按模板逐步产出可交付的 Markdown 开发文档，并为关键系统补充流程图、数据表和 HTML 原型。

## 目录

- `SKILL.md`：技能主流程，定义读取输入、确认框架、逐系统深化、收尾 Checklist 的工作方式。
- `templates/doc-structure.md`：主文档结构模板。
- `templates/system-module.md`：单个系统模块模板。
- `input/`：用户投放原始想法、脑图导出文档、参考资料。
- `output/`：生成的开发文档。
- `output/prototypes/`：系统界面 HTML 原型。
- `docs/superpowers/`：设计说明与实现计划。

## 使用流程

1. 将原始素材放入 `input/`。
2. 启动 `mindtodoc` 工作流，先汇总项目定位、核心玩法、目标平台、系统模块清单和待确认假设。
3. 用户确认系统清单后，按系统逐个深化：**规则为必选**；线上项目先定第 2 章**数据兼容总则**，各模块须**考虑红点**与**数据兼容**（版本差、转服、退盟等）；流程图、原型、数据表按需产出。
4. 所有系统完成后，生成第 4 章 Checklist，并检查 TODO 是否集中在数值策划或外部系统对接项。

## 当前样例

当前仓库已包含一份样例产物：

- `output/2026世界杯主题活动-开发文档.md`
- `output/prototypes/*.html`

这份文档已覆盖创角、新手引导、切片操作、基础关卡、养成、积分赛、淘汰赛、竞猜、排名、BP、兑换商店和礼包系统。

## 协作约定

本项目会在多设备上协作开发。每次开展新工作前先同步远端，每次完成有效改动后提交 git。

推荐流程：

```bash
git status --short --branch
git pull --ff-only
# 修改文件
git status --short
git add <changed-files>
git commit -m "<type>: <summary>"
```

如果 `git pull --ff-only` 失败，说明本地与远端出现分叉，需要先确认冲突来源再继续，避免覆盖其他设备上的改动。
