# 常用 BI 日志表字段规范

## 规范文档来源（优先级）

| 文档 | 适用范围 | 链接 / node |
|------|----------|-------------|
| **X1 / K1 / X15 公用 BI 日志表结构**（主规范） | 三项目共用 | node `ZX6GRezwJl7zDo6zhnBEDKEpVdqbropQ` · **axls** 工作簿「**X1_BI日志表说明**」；**钉钉表格 MCP** 按 Sheet 名读取（备选 `dws sheet`） |
| 常用 BI 日志表打点规范（K1 速查，与上表 user_asset 等一致） | K1 补充 | node `r1R7q3QmWe7wMo6whXXXp2MpJxkXOEP2`（adoc，可用 get_html） |
| **已有 BI 日志需求记录**（样例库） | 历史需求、四列表写法、服务器/客户端登记 | node `dpYLaezmVNLROXARIZwOlNLK8rMqPxX6` · axls「K1_BI日志统计需求」→ **钉钉表格 MCP**（备选 `dws sheet`），见 [sources.md](sources.md) |

整理需求时：**以表结构工作簿字段为准**；**命名与版式对齐样例库**；读法见 [sources.md](sources.md)。

### 公用表结构工作簿（27 个 Sheet）

钉钉表格 MCP `get_all_sheets`（node `ZX6GRezwJl7zDo6zhnBEDKEpVdqbropQ`）可得全部表名，主要包括：

**用户侧**：`user_asset`、`user_activity`、`user_event`、`user_daily`、`user_task`、`user_hero`、`user_equipment`、`user_chapter`、`user_makeup`、`user_march`、`user_trade_order`、`user_gather`、`user_battle`、`user_troop_detail`、`user_order`

**联盟/地图**：`guild_daily`、`guild_event`、`guild_asset`、`map_event_logs`、`map_point_event`

**客户端 (C)**：`user_click(C)`、`user_fte(C)`、`client_application_log(C)`、`client_fps_summary(C)`、`pb_user_event(C)`

**其它**：`notification_push`、`Reason&Event&Attr说明`（BIReason / BIEvent 枚举对照）

每个 Sheet 列结构一般为：**表名 | 字段名 | 类型 | 备注**（与下文速查一致）。

> 读 axls 表优先 **钉钉表格 MCP**，失败再 **`dws sheet`**（见 [sources.md](sources.md)）；勿依赖已失效的 get_html/OSS 路径。

## user_asset

| 字段 | 类型 | 说明 |
|------|------|------|
| reason_id | string | 定义在 bi.xml |
| reason_sub_id | string | 子场景细分 |
| reason_status | int 枚举 | 见下表 |
| asset_id | string | |
| asset_level | int | |
| change_type | int 枚举 | 1 增加；2 减少；3 镶嵌；4 取消镶嵌 |
| change_count | long | 变化值 |
| balance | long | 当前剩余值 |
| attribute1 | map | 自定义扩展 |

### reason_status

| 值 | 含义 |
|----|------|
| 0 | 无状态（瞬时：战斗、开道具、加入联盟等） |
| 1 | 开始 |
| 2 | 事件进行中 |
| 3 | 完成（**会导致资产变化**） |
| 4 | 取消 |
| 5 | 未开始直接立即完成 |
| 7 | 时间条完成（收菜类：未点收菜未真正完成，**不产生资产变化**） |

## user_event

| 字段 | 类型 | 说明 |
|------|------|------|
| event_name | string | 定义在 bi.xml |
| attribute1 | map | 自定义扩展 |

需求表模板中参数列可写 **`event_parameter`**，与 `attribute1` 等价时注明「线上字段名 attribute1」。

## user_daily

| 字段 | 类型 | 说明 |
|------|------|------|
| snapshot_value | string | JSON；key 示例：`power` 战斗力、`iap_pay` 总付费、资产 id（如 `research.suv.attk.15`）、`map_x` / `map-y` 坐标 |
| snapshot_type | string | **不可为空，默认 1**；1 玩家首条登录快照；2 当天最后状态；3 项目组自定义 |
| attribute1 | map | 自定义扩展 |

## 需求表 vs 参考图示例

参考图（如 `snow_man_attack_reward`）习惯：

- **user_asset**：多行展开 `asset_id` → `reason_id` → `reason_sub_id` → `change_type` → …
- **user_event**：`event_name` + `event_parameter`（多参数在同一单元格用列表描述）

## 梳理维度清单（从策划文档抽取）

按需裁剪，避免漏项：

1. **漏斗**：入口、主界面、子 Tab、离开
2. **资产闭环**：获得、消耗、返还、失败无变化
3. **状态机**：开始(1) / 进行中(2) / 完成(3) / 取消(4) / 时间条(7)
4. **局内节点**：探索事件、战斗、骰子、选项（偏 user_event）
5. **快照**：是否需要在 user_daily 记录截面
