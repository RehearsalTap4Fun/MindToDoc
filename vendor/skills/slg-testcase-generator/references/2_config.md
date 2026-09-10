# 配置表挖掘指南

## 🎯 使用场景

> **时机**：用例生成完成后，作为质量提升的可选步骤

PRD 中会贴一些具体的配置信息，但可能不全。用例生成后，可按本文档查找补充配置，完善用例：

| 场景 | 说明 | 补充内容 |
|------|------|----------|
| **PRD 配置不全** | PRD 只贴了部分配置 | 补充配置相关的验证用例 |
| **涉及原有功能** | 新功能关联已有系统 | 补充原有功能的配置验证 |
| **常规功能配置** | 通用功能（弹窗、解锁条件等） | 补充通用配置验证 |
| **跨表关联** | 配置中引用了其他表的 ID | 补充关联数据验证 |

---

## 📂 配置表组织结构

### 快速入口

| 资源 | 来源 | 说明 |
|------|------|------|
| **配置总文件夹** | 从 `testcase-config/project_config.md` 的「配置表总文件夹链接」获取 | 所有配置表的根目录 |
| **配置表释义** | 从 `testcase-config/project_config.md` 的「配置表释义 Sheet ID」和「配置表释义分页名」获取 | 查看对应分页 |

### 文件夹层级

> 配置表文件夹结构因项目而异，请参考 `testcase-config/project_config.md` 中的「配置表文件夹结构」章节。

### 配置表释义速查

在配置表释义表（Sheet ID 和分页名从 `testcase-config/project_config.md` 的「配置表释义 Sheet ID」和「配置表释义分页名」获取）中，可以查看：

| 列 | 说明 |
|----|------|
| A | 分类（通用/状态等） |
| B | 配置表ID和名称（如 `1011_i18n - 客户端本地化`） |
| C | 配置表简称（如 `i18n`） |
| D | Google Sheet ID |
| E+ | 各分页名称和 GID |

> 💡 **使用方法**：根据功能找到对应的配置表简称，然后用 Sheet ID 和 GID 定位到具体分页

### 分页（Sheet Tab）说明

| 分页类型 | 命名规则 | 用途 | 测试优先级 |
|----------|----------|------|:----------:|
| **功能分页** | 按功能命名（如 `85推币机`） | 前期测试环境配置 | 🥇 优先 |
| **QA** | `xxx_config_qa` | 前期测试稳定后合并的配置 | 🥈 次要 |
| **master** | `xxx_config_master` | 线上正式环境配置 | ❌ 不检查 |
| **备份** | `备份-勿删` | 历史版本备份 | ❌ 不检查 |

**分页检查流程**：

```
功能分页（前期测试）──[稳定后]──> QA 分页 ──[上线后]──> master 分页
     ↑                              ↑                      ↑
   优先检查                      次要检查              测试环境不检查
```

> ⚠️ **重要**：测试时优先查看**功能名称分页**，这是前期测试环境要检查的配置！

---

## 📋 分析步骤

### 步骤1: 定位关联配置表

**操作方法**：

1. 根据功能名称，定位到对应的配置文件夹
2. 识别主配置表和关联配置表

**示例**：测试「活动-推币机」功能

| 配置表 | 文件夹 | 用途 |
|--------|--------|------|
| `activity_config` | `21_activity/` | 活动主配置 |
| `asset_config` | `11_asset/` | 奖励资产定义 |
| `task_config` | `xx_task/` | 关联任务配置 |

### 步骤2: 识别列名规则

**列名命名规范**：

列名格式：`{端}_[数据类型]_{字段名}`

**第一部分：端标识（必须）**

| 前缀 | 含义 | 说明 |
|:----:|------|------|
| `A_` | All（全端） | 服务器和客户端都使用 |
| `S_` | Server（服务器） | 仅服务器使用 |
| `C_` | Client（客户端） | 仅客户端使用 |

**第二部分：数据类型（必须）**

| 类型 | 含义 | 示例 |
|:----:|------|------|
| `INT` | 整数 | `A_INT_id` |
| `STR` | 字符串 | `A_STR_constant` |
| `MAP` | JSON 对象 | `A_MAP_filter` |
| `ARR` | JSON 数组 | `A_ARR_activity_components` |

**完整示例**：

| 列名 | 端 | 类型 | 说明 |
|------|:--:|:----:|------|
| `A_INT_id` | 全端 | 整数 | 配置ID，服务器和客户端都用 |
| `A_STR_constant` | 全端 | 字符串 | 常量标识 |
| `A_MAP_filter` | 全端 | JSON对象 | 解锁条件 |
| `A_ARR_activity_components` | 全端 | JSON数组 | 活动组件列表 |
| `S_INT_priority` | 服务器 | 整数 | 服务器排序优先级 |
| `S_STR_comment` | 服务器 | 字符串 | 注释（仅后端参考） |
| `C_STR_banner_url` | 客户端 | 字符串 | 前端展示用的图片URL |

> 💡 **测试关注点**：`A_` 前缀字段需要同时验证客户端显示和服务器逻辑；`S_` 前缀字段主要验证服务器逻辑；`C_` 前缀字段主要验证客户端显示。

**常见字段类型**：

| 字段名 | 类型 | 测试关注点 |
|--------|------|------------|
| `id` | INT | 唯一性、引用关系 |
| `comment` | STR | 仅用于注释，不影响逻辑 |
| `filter` | MAP | 解锁条件、前置要求 |
| `components` | ARR | 功能组件列表 |
| `reward` | ARR | 奖励配置 |

### 步骤3: 解析复杂字段

**A. 解析 `A_MAP_filter` 字段**

```json
{"op":"ge","typ":"building","id":111811,"val":5}
```

| 键 | 含义 | 测试点 |
|----|------|--------|
| `op` | 操作符（ge=大于等于） | 边界值测试 |
| `typ` | 类型（building=建筑） | 类型覆盖 |
| `id` | 关联ID | 跨表查询 |
| `val` | 阈值 | 刚好/不足/超过 |

**B. 解析 `A_ARR_activity_components` 字段**

```json
[{"typ":"task","id":211510480},{"typ":"invite","id":21211019}]
```

| 键 | 含义 | 测试点 |
|----|------|--------|
| `typ` | 组件类型 | 枚举所有类型 |
| `id` | 组件ID | 跳转到对应配置表查询 |

**C. 解析 `A_ARR_calendar_reward` 字段**

```json
[{"asset":{"typ":"item","id":11111031},"setting":{"serial_number":5,"ishighlight":false}}]
```

| 键 | 含义 | 测试点 |
|----|------|--------|
| `asset.typ` | 资产类型 | 跳转 asset 表 |
| `asset.id` | 资产ID | 验证资产存在性 |
| `setting` | 显示设置 | UI 展示验证 |

### 步骤4: 跨表关联查询

**关联查询流程**：

```
activity_config (A_ARR_activity_components)
    ↓ typ="task", id=211510480
task_config (查询任务详情)
    ↓ reward_id=xxx
asset_config (查询奖励资产)
```

**记录关联关系**：

| 源表 | 源字段 | 目标表 | 目标字段 | 说明 |
|------|--------|--------|----------|------|
| activity_config | components.id | task_config | id | 活动关联任务 |
| task_config | reward_id | asset_config | id | 任务奖励 |

### 步骤5: 提取测试边界值

**从配置中提取的测试数据**：

| 配置项 | 配置值 | 测试场景 |
|--------|--------|----------|
| `filter.val=5` | 建筑等级≥5 | 等级=4（不满足）、等级=5（刚好）、等级=6（超过） |
| `priority=49996` | 显示优先级 | 多活动排序验证 |
| `calendar=1` | 显示日历 | 日历入口可见性 |

---

## 🎯 输出物

完成配置挖掘后，输出以下内容：

### 1. 配置表清单

```markdown
| 配置表名称 | Sheet ID | 分页 | 关键字段 |
|------------|----------|------|----------|
| activity_config | 1IKUBw678b2PU1m0md1vR9GxcH2uTNyLbR7VWgyAJ57E | 85推币机 | id, filter, components |
| asset_config | 1iHJdjbLv6ZbIG1RU31DiE2f0eaQoJ6jDwwxO_53L8vs | asset | id, typ, name |
```

### 2. 关联关系图

```
activity_config ──[components.id]──> task_config
                                         │
                                    [reward_id]
                                         ↓
                                    asset_config
```

---

## 📊 特殊配置处理

### JSON 数组遍历

当字段为 `A_ARR_` 类型时，需要：

1. **枚举所有元素**：确保每种 `typ` 都有测试用例
2. **验证数组边界**：空数组、单元素、多元素
3. **验证元素顺序**：如 `serial_number` 影响显示顺序

### 条件表达式解析

`A_MAP_filter` 中的操作符：

| 操作符 | 含义 | 测试策略 |
|--------|------|----------|
| `ge` | 大于等于 | 测试 val-1, val, val+1 |
| `le` | 小于等于 | 测试 val-1, val, val+1 |
| `eq` | 等于 | 测试 val-1, val, val+1 |
| `and` | 且 | 所有条件组合 |
| `or` | 或 | 任一条件满足 |

### 多分页处理

1. **确认测试环境**：QA 还是 master
2. **对比分页差异**：检查 QA 与 master 的配置差异
3. **功能分页定位**：根据功能名称找到对应分页（如 `85推币机`）

---

## 💡 提示

### 常用配置表速查

| 功能类型 | 主配置表 | 常见关联表 |
|----------|----------|------------|
| 活动 | `activity_config` | `task_config`, `asset_config` |
| 建筑 | `building_config` | `resource_config`, `time_config` |
| 商城 | `shop_config` | `asset_config`, `price_config` |
| 任务 | `task_config` | `reward_config`, `condition_config` |

### 配置表读取工具

使用 `scripts/excel_tool.py` 读取配置：

```python
from scripts.excel_tool import SheetDataReader

# 初始化读取器
reader = SheetDataReader("1IKUBw678b2PU1m0md1vR9GxcH2uTNyLbR7VWgyAJ57E")

# 列出所有分页
sheets = reader.list_sheets()

# 读取指定分页
data = reader.read_sheet(sheet_name="85推币机")

# 筛选数据
filtered = reader.filter_rows(data, {"A_INT_id": "21121101"})
```

### 注意事项

1. ⚠️ **不要直接读取整个配置表**，只读取需要的列和行
2. ⚠️ **注意分页选择**，QA 和 master 配置可能不同
3. ⚠️ **JSON 字段需要解析**，不能直接作为字符串处理
4. ⚠️ **跨表查询时记录关联路径**，便于追溯问题

---

## 📎 参考链接

### 核心入口

> 配置表入口链接因项目而异，请从 `testcase-config/project_config.md` 获取：
> - **配置总文件夹**：「配置表总文件夹链接」
> - **配置表释义**：「配置表释义 Sheet ID」+「配置表释义分页名」

### 常用配置表

> 常用配置表因项目而异，请参考 `testcase-config/project_config.md` 中的「常用配置表速查」章节。
