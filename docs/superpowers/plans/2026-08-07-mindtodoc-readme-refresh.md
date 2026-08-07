# MindToDoc README Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把根目录 README 全面刷新为面向首次使用 MindToDoc 的策划与协作人员的准确项目入口文档。

**Architecture:** 只重写根目录 `README.md`，让它负责快速上手和导航；工作流与详细规则继续链接到 `SKILL.md` 和 `references/`，不复制 SSOT。`input/` 与 `output/` 按动态工作区描述，稳定产物只通过 `examples/` 展示。

**Tech Stack:** Markdown、PowerShell、Git；Python 仅作为仓库辅助脚本的可选运行环境。

## Global Constraints

- 主要读者是首次使用 MindToDoc 的策划与协作人员。
- 主要使用模型是在 Codex 中触发 `mindtodoc` Skill，不把仓库描述成独立命令行程序。
- README 必须能独立支持首次输入、触发、审核与归档；复杂规则链接到唯一真相源。
- `input/`、`output/` 是动态工作区，不罗列其中当前项目的具体文件。
- 派生文档按事实依据创建：无截图不创建界面标注，无音频需求不创建音效需求，无分析目标不创建 BI 日志需求。
- 不修改现有业务产物；实施差异仅限 README、本设计文档状态和本计划文档。
- 文件保持 UTF-8，中文显示正常，所有相对链接目标必须存在。

---

### Task 1: 全面刷新根 README

**Files:**
- Modify: `README.md`
- Reference: `SKILL.md`
- Reference: `references/feature-spec-boundaries.md`
- Reference: `references/feature-spec-writing.md`
- Reference: `references/spec-minimalism-ladder.md`
- Reference: `references/mobile-system-rules-reference.md`
- Reference: `references/k1-common-configs.md`
- Reference: `references/ui-annotation-reference.md`
- Reference: `references/dingtalk-sync-reference.md`
- Reference: `references/audit-three-tier-discipline.md`
- Reference: `scripts/md2jsonml.py`
- Reference: `scripts/dingtalk_md_unescape.py`
- Reference: `scripts/dingtalk_table_inserter.py`
- Reference: `scripts/list_tbd.py`
- Reference: `scripts/check_plan_signatures.py`

**Interfaces:**
- Consumes: 当前目录结构、根 `SKILL.md` 的阶段流程，以及各 reference 的权威规则。
- Produces: 一个可独立支持首次上手、并把深入规则路由到 SSOT 的根 `README.md`。

- [ ] **Step 1: 重新核对实施基线**

Run:

```powershell
git status --short --branch
Get-Content -Raw -Encoding UTF8 .\README.md
Get-Content -Raw -Encoding UTF8 .\SKILL.md
```

Expected: 当前分支与用户改动清晰可见；README 仍含“骨架状态”和 `docs/superpowers/` 全部归档等过时描述；`SKILL.md` 含当前精简判断、主案/派生边界和按需交付规则。

- [ ] **Step 2: 用入口型结构重写 README**

使用 `apply_patch` 替换 `README.md`，正文按以下顺序编排，并落实每项指定内容：

1. `# MindToDoc`：说明它把脑图、框架文档、参考游戏和既有开发文档整理为可评审的移动游戏功能策划案及按需派生文档。
2. `## 核心能力`：列出素材扫描与迁移、逐模块澄清与批判性分析、主功能案、按需派生、精简审查、界面标注与钉钉同步。
3. `## 快速开始`：提供下列自然语言触发示例，并列出准备素材、触发、逐项确认、审核、可选界面/钉钉、归档六步流程。

```text
使用 mindtodoc，读取 input/ 中的素材，先逐项澄清规则，再生成主功能案和确有依据的派生文档。
```

4. `## 产物与边界`：用表格说明主案、配置表结构、界面标注、界面素材、其他派生和旧版只读迁移源；强调玩法异常在主案、Excel 字段在配置表派生、控件与 key 在界面标注。
5. `## 工作流程`：压缩说明阶段 0 输入扫描、阶段 1 整体框架、阶段 2 逐模块规则、阶段 3 按需派生、阶段 4 有图才标注、阶段 5 按需同步钉钉、完成后归档。
6. `## 目录结构`：准确说明 `SKILL.md`、`templates/`、`references/`、`scripts/`、`input/`、`output/`、`examples/`、`docs/superpowers/`；后两者分别是稳定案例和设计/实施记录，不能再写成全部旧版归档。
7. `## 关键原则`：写明本地 Markdown SSOT、一个完整功能一份主案、派生物有事实依据才创建、关键决策摘要与详细规则唯一落点、精简不得删除边界/兼容/设计意图。
8. `## 规则导航`：使用可点击相对链接路由到 `SKILL.md` 及八个 reference，不复制完整规则。
9. `## 示例项目`：只列 `examples/2026世界杯主题活动/` 与 `examples/K1新服大地图重构/`，说明它们是稳定归档案例；不列当前 `output/` 文件。
10. `## 依赖与辅助工具`：给出 `python -m pip install -r requirements.txt`，把 `requirements-dev.txt` 标为开发/校验可选依赖；用表格链接并说明五个当前脚本的用途。
11. `## 维护与协作`：保留 `git pull --ff-only` 和有效改动后提交约定；审核类任务链接 `references/audit-three-tier-discipline.md`。

- [ ] **Step 3: 验证 UTF-8、Markdown 和过时措辞**

Run:

```powershell
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
$null = $utf8.GetString([System.IO.File]::ReadAllBytes((Resolve-Path .\README.md)))
rg -n '骨架状态|已归档 \(archived\)|docs/superpowers/.+旧版' .\README.md
git diff --check
```

Expected: UTF-8 解码成功；`rg` 无匹配；`git diff --check` 无输出并返回成功。

- [ ] **Step 4: 验证 README 相对链接**

Run:

```powershell
$root = (Resolve-Path .).Path
$content = Get-Content -Raw -Encoding UTF8 .\README.md
$links = [regex]::Matches($content, '\[[^\]]+\]\((?!https?://|#)([^)#]+)(?:#[^)]*)?\)')
$missing = foreach ($link in $links) {
    $target = [System.Uri]::UnescapeDataString($link.Groups[1].Value)
    if (-not (Test-Path (Join-Path $root $target))) { $target }
}
if ($missing) { $missing; exit 1 }
```

Expected: 无输出并返回成功，表示所有 README 相对链接存在。

- [ ] **Step 5: 复核最终差异与范围**

Run:

```powershell
git status --short
git diff -- README.md docs/superpowers/specs/2026-08-07-mindtodoc-readme-refresh-design.md docs/superpowers/plans/2026-08-07-mindtodoc-readme-refresh.md
```

Expected: 未提交修改只涉及 `README.md`、设计文档状态和本计划文档；README 覆盖设计中的全部章节，且没有当前 `input/`、`output/` 具体业务文件清单。

- [ ] **Step 6: 提交 README 刷新**

Run:

```powershell
git add -- README.md docs/superpowers/specs/2026-08-07-mindtodoc-readme-refresh-design.md docs/superpowers/plans/2026-08-07-mindtodoc-readme-refresh.md
git commit -m "docs: refresh MindToDoc README"
```

Expected: 提交成功，提交内容仅包含 README、设计状态更新和实施计划。
