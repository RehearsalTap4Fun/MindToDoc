# BI 日志需求表

| 日志触发逻辑 | 日志表名/类型 | 字段名 | 字段含义/取值 |
|--------------|---------------|--------|----------------|
| 玩家把一件新秘宝装备到英雄某个部位、服务器校验通过并落库时 | user_asset | reason_id | treasure_equip（扩展已有） |
| | | attribute1 | node：时序节点 1开战/2战中/3追击/4战后；direction：方向 1进攻/2守御/3续战；stunt_id：所挂特技；stunt_lv：当前特技等级；hero_slot：1主将/2副将一/3副将二；is_active：同名比较后本件是否生效；不同特技可在同节点共同生效 |
| 玩家从英雄部位卸下一件新秘宝、服务器落库时 | user_asset | reason_id | treasure_unequip（扩展已有） |
| | | attribute1 | 字段同 treasure_equip；用于还原装备时段，计算各时刻特技的实际在装时长 |
| 秘宝入库时（商店购买、碎片合成、邮件或奖励发放） | user_asset | reason_id | treasure_add（扩展已有） |
| | | reason_sub_id | 1：KVK 商店购买；2：碎片合成整件；3：历史值保留，本期不产生；4：邮件/补偿发放 |
| | | attribute1 | node；direction；stunt_id（新秘宝才有，存量秘宝留空） |
| 玩家提交碎片合成整件或特技升级、服务器扣除碎片并写入结果时 | user_asset | reason_id | treasure_merge_cost（新增） |
| | | reason_sub_id | 1：碎片合成整件；3：碎片升级特技；历史值 2、4 保留解释但不再产生 |
| | | attribute1 | target_uid：目标实例；target_cfg_id：目标配置；stunt_id；lv_from / lv_to（整件合成为空/1）；upgrade_total_before / after：累计实际碎片投入，仅用于分解返还，不参与等级判定；shard_count：实际消耗碎片数；config_version：消耗配置版本 |
| | | event_id | 一次整件合成或升级的碎片扣除与目标结果共用同一 event_id，重复请求不重复记录 |
| 一场战斗结算后，对每支部队、每条实际生效并触发的时序特技各记一条（交战双方分别记录） | user_event | event_name | treasure_stunt_trigger（新增） |
| | | event_parameter | battle_id：与 user_battle 同一场战斗的 ID；node：触发节点；stunt_id；stunt_lv；影响值 effect_value：按特技类型分别为额外造成伤害/减免伤害/免疫伤害/回战士兵数/恢复士兵数；troop_role：1进攻方/2防守方；battle_result：胜/负/无胜负；rounds：本场回合数；is_real_battle：是否满足真实交战判定 |
| 真实交战胜利授予乘胜，或真实交战有胜负且本方存活授予坚守时；以及效果被下一场消耗或作废时，各记一条 | user_event | event_name | treasure_carry_effect（新增） |
| | | event_parameter | stage：1授予/2被下一场消耗/3作废（窗口到期、回城、解散、全灭或迁服）；stunt_id；stunt_lv；grant_battle_id：授予场战斗 ID；use_battle_id：生效场战斗 ID（stage=2 才有）；window_left：消耗时剩余窗口秒数 |
| 玩家首次满足王国纪事解锁条件、秘宝系统对其开放时 | user_event | event_name | treasure_system_unlock（新增） |
| | | event_parameter | unlock_svs：触发解锁的王国纪事节点 ID；city_level：解锁时城堡等级 |
| 玩家在现有秘宝背包的分解弹窗确认提交，整批实例移除与资源返还一并成功时 | user_asset | reason_id | treasure_decompose（新增） |
|  |  | reason_sub_id | 1：橙色分解返还秘宝碎片；2：低品质分解返还破碎大陆金币 |
|  |  | attribute1 | treasure_uid：被分解实例；treasure_cfg_id：配置；quality：品质；stunt_lv：特技等级（存量为空）；base_return：基础返还；upgrade_return：升级投入返还（低品质及无投入为0）；return_count：该实例返还总数；config_version：返还配置版本。逐实例记录，批量不丢失来源 |
|  |  | event_id | 同一批分解的实例移除、碎片与金币发放共用同一 event_id，逐实例明细与聚合资产流水不得重复计收入。回收与投放分开统计，重放不重复记录 |

# 待确认项

- `treasure_stunt_trigger` 的量级：按每场战斗每方每条生效特技各一条计，近 7 天 PVP 战斗约 93 万场、主副将同节点不同特技均可生效，单部队最多 12 种特技，峰值可达千万级/周。需与数据确认是全量记录、按服务器抽样，还是只记"影响值大于阈值"的触发。
- `effect_value` 的口径需与战斗程序统一：伤害类与士兵数类是两种量纲，是分列记录还是共用一列加 `effect_type` 标识。
- `is_active`（本件在同名比较后是否生效）由服务端在装备时算出并落日志，还是分析侧按同部队同名特技的等级及英雄顺序自行推导，影响是否需要该字段。
- 碎片的标准增减（获得与消耗）按框架默认写入 `user_asset`，本表未列。
  - 若数据侧需要按来源拆分碎片获得（配置的任务 / 商店 / 奖励），需要在碎片的 `treasure_shard_add` 上追加 `reason_sub_id`，届时补一行。
