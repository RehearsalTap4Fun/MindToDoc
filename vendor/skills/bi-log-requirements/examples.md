# 示例



## 工作流摘要（巨龙培育）



1. 读策划 adoc：`XPwkYGxZV3R4Xdz4Cgqr3w9qWAgozOKL`（dws doc get_document_content）

2. **询问**是否需要客户端日志（默认否）

3. 查代码已有 `reason_id` / `event_name`，剔除已有打点与默认资产流水

4. 对照样例「日志需求举例」的四列表展开方式

5. 输出需求 + 可选 Excel



## 四列表片段（仅新需求）



| 日志触发逻辑 | 日志表名/类型 | 字段名 | 字段含义/取值 |

|--------------|---------------|--------|----------------|

| 玩家探索关卡战斗胜利、服务器发放关卡奖励时 | user_asset | reason_id | dragon_breed_explore_reward（新增，bi.xml） |

| | | reason_sub_id | 1：首通；2：重复探索 |

| | | attribute1 | stage_id；juvenile_dragon_id |

| 探索关卡内单场战斗结算时 | user_event | event_name | dragon_breed_explore_battle（新增，bi.xml） |

| | | event_parameter | stage_id；result：胜/败 |



> `vip_exp_add` 等**已有** reason、道具标准增减流水**不出现在表中**。



## Excel 数据结构



`write_workbook` 接受的 `groups` 为 Python 列表，直接在代码中构造：



```python

from pathlib import Path

from gen_bi_requirements_excel import write_workbook



groups = [

    {

        "trigger": "玩家探索关卡战斗胜利、服务器发放关卡奖励时",

        "table": "user_asset",

        "fields": [

            ["reason_id", "dragon_breed_explore_reward（新增，bi.xml）"],

            ["reason_sub_id", "1：首通；2：重复"],

            ["attribute1", "stage_id；juvenile_dragon_id"],

        ],

    },

]



write_workbook(Path("./巨龙培育_BI日志需求.xlsx"), groups)

```



## 样例库中的 user_asset 链式打点（建筑建造）



同一 `event_id` 贯穿开始/完成；`reason_status`：开始=1，完成=3。  

详见 node `dpYLaezmVNLROXARIZwOlNLK8rMqPxX6` · Sheet「日志需求举例」。



## 案例：VIP 至尊特权（精简版）



**写进需求表（5 条）：**



```python

groups = [

    {

        "trigger": "玩家至尊转盘抽奖（含1/10/100倍）结算发奖时",

        "table": "user_asset",

        "fields": [

            ["reason_id", "vip_supreme_turntable_reward（新增，bi.xml）"],

            ["reason_sub_id", "1：普通；2：城堡碎片；3：行军碎片；4：商店点数"],

            ["attribute1", "roulette_cfg_id；is_guarantee；spin_seq；guarantee_tier"],

            ["event_id", "10/100倍批量转动时各奖励行共用"],

        ],

    },

    # user_event：入口解锁、保底触发、皮肤完成全服通知、VIP20积分补偿

]

```



**不写进需求表：** 转盘积分获得/消耗、商店买卖、拼图扣碎片、装扮发放、`vip_exp_add`、VIP 商店；客户端 `user_click`（未向用户确认前）。


