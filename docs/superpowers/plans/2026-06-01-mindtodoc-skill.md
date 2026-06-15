> **ARCHIVED — 历史文档，勿作实现依据**
>
> 归档日期：2026-06-15。本文档为 2026-06-01 **旧版** MindToDoc 的实现计划（四段式开发文档 + `ui-ux-pro-max` HTML 原型 + `output/prototypes/`）。
>
> **现行规范**：[SKILL.md](../../../SKILL.md)（对齐项目组 `system-design-doc` 定稿）；界面走 `-界面标注.md` 截图红圈流程，**不再**生成 HTML 原型。

# MindToDoc 技能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 `mindtodoc` 技能，把粗糙的移动游戏想法转化为高度专业、可直接开发的 md 文档。

**Architecture:** Superpowers 风格 Skill。`SKILL.md` 承载流程与交互逻辑；`templates/` 下两个 md 模板是专业文档结构的唯一真相来源；`input/` 收素材，`output/` 出文档与 HTML 原型。流程图与界面原型软依赖社区 mermaid 技能和 `ui-ux-pro-max`，未装则降级为手写。

**Tech Stack:** Markdown（技能与模板）、Mermaid（流程图）、HTML/Tailwind（原型，经 ui-ux-pro-max）。

**适配说明:** 本项目产出为 markdown 散文，非可执行代码；当前目录已接入 git。故"测试"= spec 定义的最小样例跑通验证；协作开发时每次开展新工作前先 `git pull --ff-only`，每次完成有效改动后提交 git。

---

## File Structure

```
MindToDoc/
├── SKILL.md                  # 技能主文件：frontmatter + 流程 + 提问逻辑 + 降级规则
├── templates/
│   ├── doc-structure.md      # 主文档骨架（4 章）
│   └── system-module.md      # 单系统模块小节模板
├── input/.gitkeep            # 素材投放目录
└── output/                   # 生成产物（运行时填充）
    └── prototypes/.gitkeep
```

- `SKILL.md` 只管"怎么做"（流程/交互），不内嵌文档结构正文。
- 两个模板只管"产出长什么样"，纯骨架、无流程逻辑。职责分离，各自可独立修改。

---

### Task 1: 创建目录骨架

**Files:**
- Create: `MindToDoc/input/.gitkeep`
- Create: `MindToDoc/output/prototypes/.gitkeep`

- [ ] **Step 1: 创建占位文件**

两个 `.gitkeep` 内容均为空。创建后确认目录树为：
```
MindToDoc/input/.gitkeep
MindToDoc/output/prototypes/.gitkeep
```

- [ ] **Step 2: 验证**

Run: `find MindToDoc/input MindToDoc/output -type d`
Expected: 列出 `MindToDoc/input`、`MindToDoc/output`、`MindToDoc/output/prototypes`

---

### Task 2: 编写主文档模板 doc-structure.md

**Files:**
- Create: `MindToDoc/templates/doc-structure.md`

- [ ] **Step 1: 写入主文档骨架**

```markdown
# {{游戏名}} 开发文档

> 目标平台：{{平台}} | 参考对标：{{参考游戏}} | 生成日期：{{日期}}

## 1. 概述

- **一句话定位**：{{定位}}
- **核心玩法**：{{核心玩法}}
- **参考游戏对标**：{{参考游戏}} —— {{对标要点}}
- **目标平台**：{{平台}}

## 2. 核心玩法机制

- **玩法循环**：{{玩法循环}}
- **全局规则**：{{全局规则}}
- **数值框架**：{{数值框架}}

## 3. 系统设计

<!-- 每个系统插入一份 system-module.md，编号 3.1 / 3.2 / ... -->

## 4. Checklist

<!-- 开发交付检查清单，按系统逐项勾选 -->
- [ ] {{系统名}}：规则已确认 / 流程图完成 / 原型完成 / 数据表完成
```

- [ ] **Step 2: 验证**

Run: `grep -c "^## " MindToDoc/templates/doc-structure.md`
Expected: `4`（四个章节标题）

---

### Task 3: 编写系统模块模板 system-module.md

**Files:**
- Create: `MindToDoc/templates/system-module.md`

- [ ] **Step 1: 写入单系统模块骨架（小节顺序：规则→流程图→原型→数据表）**

```markdown
### 3.{{序号}} {{系统名}}

#### 规则与逻辑

{{该系统的规则、状态、约束、与其他系统的关系}}

#### 流程图

```mermaid
{{流程图 / 状态机，描述本系统核心流转}}
```

#### 界面原型

- 原型文件：[output/prototypes/{{系统英文名}}.html](../output/prototypes/{{系统英文名}}.html)
- 关键交互要点：{{要点说明}}

#### 数据结构 / 配置表

| 字段 | 类型 | 说明 | 取值范围 |
|------|------|------|----------|
| {{字段}} | {{类型}} | {{说明}} | {{范围}} |
```

- [ ] **Step 2: 验证**

Run: `grep -E "^#### " MindToDoc/templates/system-module.md`
Expected: 四行 —— `规则与逻辑`、`流程图`、`界面原型`、`数据结构 / 配置表`，顺序一致

---

### Task 4: 编写 SKILL.md（frontmatter + 流程主干）

**Files:**
- Create: `MindToDoc/SKILL.md`

- [ ] **Step 1: 写入 frontmatter 与流程**

```markdown
---
name: mindtodoc
description: 把粗糙的移动游戏想法（脑图、框架文档、参考游戏名）转化为高度专业、可直接开发的 md 文档。读取 input/ 素材，逐系统确认细节并补充流程图与交互原型，输出到 output/。Use when 用户要把游戏创意整理成开发文档、生成游戏开发文档、game design doc。
---

# MindToDoc

把 `input/` 下的粗糙游戏想法，转化为 `output/<游戏名>-开发文档.md` ——
一份高度专业、可直接用于开发的文档。

## 产出位置

- 主文档：`output/<游戏名>-开发文档.md`
- 界面原型：`output/prototypes/<系统英文名>.html`
- 文档结构来自 `templates/doc-structure.md` 与 `templates/system-module.md`，
  这两个模板是专业结构的唯一真相来源，按需修改它们而非硬编码结构。

## 流程

### 阶段 0 · 读取输入
扫描 `input/`，读取脑图、框架文档、参考游戏名等所有素材并消化。
若 `input/` 为空：提示用户先放入素材，停止，不硬跑。

### 阶段 1 · 确认整体框架
向用户汇报从输入中理解到的：游戏定位、核心玩法、目标平台，以及拆出的
**系统模块清单**及优先级。列出任何"待确认假设"（残缺/矛盾/仅有参考游戏名处），
由用户拍板，不擅自编造。用户确认系统清单后，按 `doc-structure.md` 产出第 1、2 章。

### 阶段 2 · 逐系统深入
对系统清单中每个系统，按顺序循环：
1. **确认规则细节** —— 追问该系统的空白点，直到规则清晰
2. **生成流程图** —— 见「外部技能与降级」
3. **生成界面原型** —— 见「外部技能与降级」
4. **生成数据结构/配置表** —— 实体、字段、类型、取值范围
5. 用户确认 → 按 `system-module.md` 把该模块追加进主文档 → 下一个系统

单个系统出错或返工不影响其他系统。

### 阶段 3 · 收尾
生成第 4 章 Checklist（按系统逐项），输出完整主文档。

## 外部技能与降级（软依赖）

- **流程图**：优先调用社区 mermaid 技能；未装则直接手写 Mermaid 代码块，
  并在该处留一行提示「mermaid 技能未安装，已手写」。
- **界面原型**：优先调用 `ui-ux-pro-max` 生成 HTML 原型存入 `output/prototypes/`；
  未装则手写 HTML/线框示意，并留一行提示。

核心流程不依赖第三方技能，任何情况下都能产出文档。
```

- [ ] **Step 2: 验证 frontmatter 合法**

Run: `head -4 MindToDoc/SKILL.md`
Expected: 第 1 行 `---`，第 2 行 `name: mindtodoc`，含 `description:`，第 4 行 `---`

- [ ] **Step 3: 验证流程完整**

Run: `grep -E "^### 阶段" MindToDoc/SKILL.md`
Expected: 四行，阶段 0/1/2/3 齐全

---

### Task 5: 最小样例端到端验证

**Files:**
- Create: `MindToDoc/input/sample-idea.md`（临时验证用，验证后删除）

- [ ] **Step 1: 放入最小样例素材**

```markdown
# 想法：roguelike 卡牌手游

玩家组建卡组，逐层闯关，每层战斗后三选一获得新卡或遗物。
参考游戏：杀戮尖塔（Slay the Spire）。
目标平台：iOS / Android。
```

- [ ] **Step 2: 手动跑一遍技能流程（模拟，不依赖会话）**

按 `SKILL.md` 流程，对该样例走阶段 0→3，至少完整产出 1 个系统模块
（如"战斗系统"：规则 + Mermaid 流程图 + 原型链接 + 数据表）。
产出写到 `output/roguelike-卡牌手游-开发文档.md`。

- [ ] **Step 3: 验证产出结构正确**

Run: `grep -E "^(# |## |### 3\.|#### )" MindToDoc/output/*.md`
Expected: 含一级标题、第 1-4 章、至少一个 `### 3.x 系统`、该系统下四个 `####` 小节
（规则与逻辑 / 流程图 / 界面原型 / 数据结构）

- [ ] **Step 4: 清理临时文件**

删除 `MindToDoc/input/sample-idea.md` 与验证产出，保持目录干净。
（若日后 init git 仓库：此处可 `git add MindToDoc && git commit -m "feat: mindtodoc skill"`）

---

## Self-Review

- **Spec coverage:** 目录结构(Task1) / 主文档结构(Task2) / 系统模块小节顺序 A(Task3) / 形态+四阶段流程+降级+边界(Task4) / 验证方式(Task5) —— spec 各节均有对应任务，无遗漏。
- **Placeholder scan:** 模板中的 `{{...}}` 是运行时占位变量（设计的一部分），非计划占位符；各步骤均含实际内容与命令。
- **Type consistency:** 文档章节编号（1-4）、系统小节四项名称在 Task2/3/4/5 间一致；`output/prototypes/` 路径在模板与 SKILL.md 间一致。
