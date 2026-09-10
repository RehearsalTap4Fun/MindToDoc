---
name: bi-log-requirements
description: >-
  X1/K1/X15 三项目通用：从功能策划文档生成 BI 日志需求。结合公用表结构工作簿、K1 需求样例库、
  四列表交付模板，优先用钉钉表格 MCP 读取 axls、用钉钉文档 MCP/dws 读取 adoc，输出 Markdown 或 Excel。
  触发词：BI日志需求、BI需求表、整理埋点、根据文档生成BI、reason_id 需求、user_asset 需求、生成 BI Excel。
---

# 根据文档生成 BI 日志需求（X1 / K1 / X15）

从**功能策划文档**产出**字段级 BI 需求**（四列表），供数据、服务器、客户端对齐。  
查**代码里已有打点**用 [k1-bi-tracking](../k1-bi-tracking/SKILL.md)；本 skill 负责**新功能需求撰写**。

## 前置条件

- **钉钉表格 MCP**（`user-钉钉表格`，已配置于 Cursor MCP）读取 **axls** 电子表格为**首选**；**钉钉文档 MCP**（`user-钉钉文档` / `user-dingtalk-doc`）读取 **adoc** 文档
- **MCP 不可用、鉴权失败或工具报错时**，回退到 **`dws` CLI**（Windows 常见路径：`%USERPROFILE%\.local\bin\dws.exe`），所有 `dws` 命令加 **`--format json`**
- 读钉钉内容**禁止** curl/浏览器替代（见 [sources.md](sources.md)、[dws](../dws/SKILL.md) 禁止项）

## 项目区分（影响 bi.xml 相关动作）

| 项目 | 仓库标识 | reason 登记位置 |
|------|----------|----------------|
| **X1 / X15** | 仓库含 `bi.xml` | `bi.xml` + `const.go` |
| **K1** | 仓库 `dataconfig`（无 `bi.xml`） | 仅 `const.go` |

- 在 **K1 仓库（`dataconfig`）** 下工作时，**不要**生成、修改、引用 `bi.xml`，也不要在交付物里写「需 bi.xml 登记」
- 判断方式：工作目录根名 / 仓库内是否存在 `bi.xml`

## 权威数据源（固定 node）

| 用途 | nodeId | 名称 | 读取方式 |
|------|--------|------|----------|
| **表结构规范** | `ZX6GRezwJl7zDo6zhnBEDKEpVdqbropQ` | X1_BI日志表说明 | 钉钉表格 MCP 优先；回退 `dws sheet` · 27 个 Sheet，每 Sheet = 一张 BI 表字段定义 |
| **需求样例库** | `dpYLaezmVNLROXARIZwOlNLK8rMqPxX6` | K1_BI日志统计需求 | 钉钉表格 MCP 优先；回退 `dws sheet` · `日志需求举例` / `服务器日志` / `客户端日志` |
| **Reason/Event 枚举** | 同上（表结构工作簿） | Sheet `Reason&Event&Attr说明` | 查 `BIReason` / `BIEvent` 命名是否可复用 |

详情与命令：[sources.md](sources.md)

## 标准工作流（必须按序）

```
[1] 读功能策划文档
      ↓
[2] 拆业务行为清单（可验收）
      ↓
[2.5] 询问用户是否需要客户端日志（未明确前默认仅服务器）
      ↓
[3] 查代码/k1-bi-tracking → 剔除已有打点 & 默认资产流水
      ↓
[4] 查表结构 Sheet + 样例库 → 确定仍需登记的日志
      ↓
[5] 输出四列表（Markdown / Excel，默认仅服务器）
      ↓
[6] 自检清单
```

## 需求范围（必守，生成前过滤）

> **BI 需求表 ≠ bi.xml reason 登记清单。**  
> 开发实现时新增的 `reason_id` 在 `bi.xml` / `const.go` 配置即可；**只有数据分析侧需要额外约定语义时**，才写入本需求表。

### 1. 已有 reason_id / event_name → 核验覆盖后省略或保留增量

生成前用 [k1-bi-tracking](../k1-bi-tracking/SKILL.md) 或 `game/bi/def/const.go` 查重。  
枚举存在只证明名字已登记。须读取实际打点调用及载荷，对照本次分析目标核验触发分支、字段、取值语义和关联 ID；全部覆盖才省略，不在需求表重复列纯复用项。同名事件需要新增字段、取值或触发条件时，保留差异并标「扩展已有」，引用原实现作为基线。未查到调用或无法验证时保留待核查状态，不能据枚举名判定零新增。

> **K1 枚举命名查重看 `const.go`，行为覆盖还须查实际调用代码**，不要查 / 提及 `bi.xml`。X1/X15 的枚举登记另外核对 `bi.xml`。

### 2. 标准资产流水 → 不写进需求表（含「仅为新 reason 起名」）

新道具、新积分、新货币经 `AddAssets` / `DecAssets` 流转时，框架**自动**写入 `user_asset`（`asset_id`、`change_type`、`change_count`、`balance` 等标准字段）。

以下情况**一律不进需求表**，由开发在代码里挂 reason 即可：

| 不写进需求表 | 说明 |
|--------------|------|
| 新货币/道具**获得** | 如至尊转盘积分同步、商店购买得道具 |
| 新货币/道具**消耗** | 如转动扣积分、商店扣点数 |
| 碎片提交、皮肤/装扮发放 | 若走标准增减且无额外分析维度 |
| 已有 reason 的业务 | 如 `vip_exp_add`、`vip_shop_add` / `vip_shop_dec` |

**反例（常见误判）**：不要因「起了新 reason 名」就单独写一行——  
`vip_supreme_turntable_point_add`、`vip_supreme_turntable_cost`、`vip_supreme_shop_dec`、`vip_supreme_shop_add` 都属于标准流水，**不应出现在需求表**。

### 3. user_asset 何时才写进需求表

仅当标准流水**覆盖不了**，且需与数据/服务器**对齐额外约定**时：

| 要写 | 说明 | 示例 |
|------|------|------|
| `reason_sub_id` 语义 | 同 reason 下需区分场景做分析 | 1 普通奖励；2 城堡碎片；3 行军碎片 |
| `attribute1` 业务维度 | 标准字段不够用 | `spin_seq`、`is_guarantee`、`guarantee_tier` |
| `event_id` 串联规则 | 一批操作多条 asset 须同 id | 10/100 倍转盘批量奖励 |

需求表里**只写** `reason_id`、`reason_sub_id`、`attribute1`、`event_id` 等需约定的行；**不要**重复列 `asset_id` / `change_count` / `balance`。

### 4. user_event 何时写

偏**流程/状态/通知**，不承载资产台账，或需独立于 asset 留痕时写 `user_event`，例如：

- 功能入口首次解锁
- 保底机制触发（便于分析，与 asset 奖励行互补）
- 全服广播/跑马灯类节点
- 一次性补偿/迁移

### 5. 客户端日志 → 先问用户，默认不生成

`user_click(C)` 等**仅在特定场景**需要（漏斗、入口曝光等）。

- **生成前必须先问**：「是否需要客户端点击日志？」
- 用户**未明确肯定** → **只输出服务器日志**
- 用户确认需要 → 再补 `user_click(C)`

### 案例：VIP 至尊特权（精简后应保留什么）

| 写进需求表 | 不写进需求表 |
|------------|--------------|
| `user_asset` · `vip_supreme_turntable_reward`（`reason_sub_id` + 保底相关 `attribute1`） | 转盘积分获得/消耗、商店买卖、拼图扣碎片、装扮发放 |
| `user_event` · 入口解锁、保底触发、皮肤完成全服通知、VIP20 积分补偿 | `vip_exp_add`、VIP 商店、`user_click`（未确认前） |

### Step 1：读功能策划文档

1. **类型探测**：钉钉文档 MCP `get_document_info`（首选）或 `dws doc info --node "<URL或nodeId>" --format json` → 看 `extension`
2. **adoc**：钉钉文档 MCP `get_document_content` / `user-dingtalk-doc` `get_html`（备选 `dws doc get_document_content --node "<nodeId>" --format json`）
3. **axls**（策划文档本身是表格时）：钉钉表格 MCP `get_all_sheets` + `get_range`（备选 `dws sheet`）
4. 提取：模块、资源闭环、状态机、战斗/行军、客户端点击、是否需快照

### Step 2：拆业务行为

按模块列出**可验收**条目，例如：「探索关卡胜利发奖」「孵化开始扣龙蛋」「打开活动主界面」。  
每条后续对应 0~N 条日志（可多表组合）。

### Step 2.5：确认客户端日志范围

向用户确认是否需要 `user_click(C)` 等客户端日志。  
**默认假设：不需要**，除非用户明确说要。

### Step 3：查已有打点，过滤需求范围

1. 用 k1-bi-tracking / `git grep` 查 `reason_id`、`event_name` 是否已存在
2. 核对实际调用的触发、字段与语义；剔除完全覆盖当前目标的打点和标准资产流水，保留同名日志的增量约定（见上文「需求范围」）
3. 剩余条目再决定是否需要新 `reason_id`、`user_event`、`user_makeup` 等

### Step 4：选表 + 字段（查表结构工作簿）

**首选**钉钉表格 MCP：

1. `get_all_sheets({ nodeId: "ZX6GRezwJl7zDo6zhnBEDKEpVdqbropQ" })`
2. `get_range({ nodeId, sheetId, range: "A1:D30" })` 读对应 Sheet

**备选**（MCP 失败时）：`dws sheet list --node ZX6GRezwJl7zDo6zhnBEDKEpVdqbropQ`，再 `dws sheet range read --sheet-id <id> --range "A1:D30"`

**快速路由**（完整 27 表见 [reference.md](reference.md)）：

| 策划内容 | 日志表 |
|----------|--------|
| 道具/货币增减、镶嵌、余额 | `user_asset` |
| 行为/曝光/流程，无资产台账 | `user_event` |
| 登录/日末截面、战力/付费/坐标 | `user_daily` |
| 任务状态变化 | `user_task` |
| 英雄/技能/装备变化 | `user_hero` / `user_equipment` |
| 关卡/章节 | `user_chapter` |
| 战斗结算 | `user_battle`（注意 `event_id` 与 asset 一致） |
| 行军/采集 | `user_march` / `user_gather` |
| 客户端点击 | `user_click(C)` |
| 联盟相关 | `guild_*` |

**脚本辅助**（内部仍走 dws，MCP 不可用时可用；按 Sheet 名拉字段）：`python scripts/fetch_table_fields.py --table user_asset`

### Step 5：对照样例库

node `dpYLaezmVNLROXARIZwOlNLK8rMqPxX6`（**钉钉表格 MCP** 读取，失败再 dws）：

| Sheet | 用途 |
|-------|------|
| **日志需求举例** | 四列表**字段展开**范例（user_asset 多行、event_id 一致、reason_status 1/3） |
| **服务器日志** | 登记格式：模块 / 版本 / 负责人 / 触发逻辑 / **表名** |
| **客户端日志** | `user_click` 等客户端登记格式 |

对齐规则：

- **user_asset** 需求表只展开需约定项：`reason_id` → `reason_sub_id` → `attribute1` → `event_id`（不写标准流水字段）
- **user_event**：`event_name` + `event_parameter`（含义列写 map key；线上常为 `attribute1`）
- 有**开始—完成**链路：`reason_status` 写 1/2/3/4/5/7（见 [reference.md](reference.md)）
- 同一流程多条 asset：**event_id 保持一致**（样例「建筑建造」）
- 新 `reason_id` / `event_name`：在 `Reason&Event&Attr说明` 查重；无则标「**新增**」（**X1/X15** 额外注明「需 bi.xml 登记」；**K1（dataconfig）** 不写 bi.xml 字样）
- 纯复用不写进交付表；同名但存在字段、取值或触发差异的标「扩展已有」，只写差异与基线依据。

### Step 6：输出四列表

**列名固定**（一张连续表，不要插模块小标题行）：

| 日志触发逻辑 | 日志表名/类型 | 字段名 | 字段含义/取值 |

**日志触发逻辑**列：写**何时 / 在什么条件下**记这条日志（触发时机、前置条件），不写功能模块名。  
规则见 [output-format.md](output-format.md)。

**生成 Excel**：在 Python 中构造 `groups` 后调用 `write_workbook`，**勿经 JSON 文件或 JSON 字符串中转**：

```python
from pathlib import Path
import sys
sys.path.insert(0, "scripts 所在目录")
from gen_bi_requirements_excel import write_workbook

write_workbook(Path("输出路径.xlsx"), groups=[...])
```

`groups` 结构见 [examples.md](examples.md)。**新建文件前**若路径未指定须与用户确认。

### Step 7：自检

- [ ] 已询问客户端日志；未确认时输出中**无** `user_click(C)`
- [ ] 已核对实际调用的触发和字段语义；纯复用条目已剔除，同名日志的扩展需求未误删
- [ ] **无**仅为新货币/道具增减而写的 user_asset 行（**新 reason 名 alone 不算需求**）
- [ ] user_asset 行仅含需约定的 `reason_sub_id` / `attribute1` / `event_id`，无标准字段堆砌
- [ ] 每条对应策划文档中**数据分析侧仍需对齐**的行为，而非开发配置清单
- [ ] 字段均来自表结构 Sheet，无臆造列
- [ ] 资产类未误用 `user_event`（反之亦然）
- [ ] `reason_status` 与是否真产生资产变化一致（**3** vs **7**）
- [ ] 多条 user_asset 同流程 **event_id** 是否需一致
- [ ] 新增 reason/event 已标注「**新增**」（X1/X15 注明「需 bi.xml 登记」；K1 不写 bi.xml）
- [ ] 当前仓库为 K1（dataconfig）时，全文**未出现** `bi.xml`

## 与其它 skill 边界

| skill | 职责 |
|-------|------|
| **本 skill** | 策划文档 → BI **需求表** |
| k1-bi-tracking | 查代码/SQL **已有**打点 |
| 钉钉表格 MCP | 读 axls 的**首选**工具 |
| dws | 读钉钉文档/表格的**备选**工具 |
| dev-checklist-generator | 开发任务拆解，非 BI 字段表 |

## 参考文件

- [reference.md](reference.md) — 常用表字段、27 Sheet 清单、reason_status
- [sources.md](sources.md) — MCP / dws 读表命令、node 说明
- [output-format.md](output-format.md) — 四列表与 Excel 规范
- [examples.md](examples.md) — groups 样例、巨龙培育片段
