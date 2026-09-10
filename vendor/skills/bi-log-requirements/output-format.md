# 四列表输出规范

项目组交付模板（与 K1 样例库、雪人活动等参考图一致）。

## 表头（固定）

| 日志触发逻辑 | 日志表名/类型 | 字段名 | 字段含义/取值 |

- **一张连续表**，不要按模块插入额外标题行
- 无某类日志时：省略该行
- **日志触发逻辑**：写**何时 / 在什么条件下**记录这条日志（触发时机与前置条件），不要写功能模块名或界面名称

## 同一功能多字段

**user_asset** 典型展开（只写需约定项，标准流水字段不列）：

| 日志触发逻辑 | 日志表名/类型 | 字段名 | 字段含义/取值 |
|--------------|---------------|--------|----------------|
| 玩家至尊转盘抽奖（含1/10/100倍）结算发奖时 | user_asset | reason_id | vip_supreme_turntable_reward（新增，bi.xml） |
| | | reason_sub_id | 1：普通奖励；2：城堡碎片；3：行军碎片 |
| | | attribute1 | is_guarantee；spin_seq；guarantee_tier |
| | | event_id | 批量转动时各奖励行共用 |

**user_event** 典型展开：

| 日志触发逻辑 | 日志表名/类型 | 字段名 | 字段含义/取值 |
|--------------|---------------|--------|----------------|
| 玩家抽中雪人活动大奖、服务器确认发奖时 | user_event | event_name | snow_man_big_reward |
| | | event_parameter | itemId：物品 ID；itemNum：数量；round：当前轮次 |

> 交付列名用 `event_parameter`；若线上字段为 `attribute1`，在含义列注明。

## Excel

- 第 1 行：表头
- 自第 2 行起：数据；**日志触发逻辑、日志表名** 列纵向合并
- 脚本：`scripts/gen_bi_requirements_excel.py`

## 命名约定

- 需求阶段可用蛇形占位：`dragon_breed_explore_reward`
- 新 reason/event 标「新增」；已有日志的字段、取值或触发差异标「扩展已有」。仅 X1/X15 新枚举注明需 bi.xml 登记，K1 使用 const.go。
- 纯复用条目不写；实际调用完全覆盖本次目标才省略，不能仅凭枚举同名排除扩展需求。
- 查重：`ZX6GRezwJl7zDo6zhnBEDKEpVdqbropQ` → Sheet `Reason&Event&Attr说明`；代码侧查 `game/bi/def/const.go`

## 核心原则

**BI 需求表 ≠ bi.xml reason 登记清单。** 开发新增 reason 在代码里配置；需求表只写数据分析需要额外约定的部分。

## 不写进需求表的情况

| 情况 | 处理 |
|------|------|
| 实际打点的触发、字段与语义完全覆盖本次目标 | 省略；不写纯复用项，同名但有差异时保留增量 |
| 新道具/积分/货币的**标准增减** | 框架默认 `user_asset`，省略 |
| **仅为新 reason 起名**的获得/消耗 | 如 `*_point_add`、`*_cost`、`*_shop_dec/add`，省略 |
| 碎片提交、装扮发放（无额外分析维度） | 标准流水，省略 |
| 客户端点击日志 | **先问用户**；未确认则不写 |

## user_asset 何时仍要写

同时满足：**标准流水不够** + **需与数据对齐约定**。只写 `reason_id`、`reason_sub_id`、`attribute1`、`event_id` 等扩展项；**不要**列 `asset_id` / `change_count` / `balance`。

典型应写：`reason_sub_id` 分场景、保底/批次类 `attribute1`、批量操作 `event_id` 规则。  
典型不写：新货币获得/消耗、商店买卖、纯道具发放。

## user_event 何时写

入口解锁、保底触发、全服通知、一次性补偿等**流程节点**，用 `event_name` + `event_parameter`。

## 服务器 vs 客户端

- **默认只交付服务器日志**（`user_asset` 新 reason 约定 / `user_event` / `user_makeup` 等）
- **客户端**（`user_click(C)`）：用户明确需要后再补充；样例库见 Sheet「客户端日志」
