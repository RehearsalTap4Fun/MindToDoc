# BI 日志需求表

| 日志触发逻辑 | 日志表名/类型 | 字段名 | 字段含义/取值 |
|--------------|---------------|--------|----------------|
| 玩家把一件新秘宝装备到英雄某个部位、服务器校验通过并落库时 | user_asset | reason_id | treasure_equip（扩展已有） |
| | | attribute1 | node：时序节点 1开战/2战中/3追击/4战后；direction：方向 1进攻/2守御/3续战；stunt_id：所挂特技；stunt_lv：当前特技等级；hero_slot：1主将/2副将一/3副将二；is_active：该节点下本件是否为生效的那一条 |
| 玩家从英雄部位卸下一件新秘宝、服务器落库时 | user_asset | reason_id | treasure_unequip（扩展已有） |
| | | attribute1 | 字段同 treasure_equip；用于还原装备时段，计算各时刻特技的实际在装时长 |
| 秘宝入库时（商店购买、碎片合成、真实交战掉落三种来源） | user_asset | reason_id | treasure_add（扩展已有） |
| | | reason_sub_id | 1：KVK 商店购买；2：碎片合成整件；3：真实交战掉落；4：邮件/补偿发放 |
| | | attribute1 | node；direction；stunt_id（新秘宝才有，存量秘宝留空） |
| 玩家提交秘宝合成、服务器销毁材料并写入结果时（碎片合成整件与同名合成升等级两类共用一条 reason，用 reason_sub_id 区分） | user_asset | reason_id | treasure_merge_cost（新增） |
| | | reason_sub_id | 1：碎片合成整件；2：同名件合成提升特技等级 |
| | | attribute1 | target_uid：目标秘宝实例；target_cfg_id：目标配置；stunt_id；lv_from / lv_to：特技等级变化（碎片合成整件时 lv_from 留空、lv_to 固定 1）；merge_total：本次合并后的累计同名件数；material_count：本次消耗材料件数或碎片数 |
| | | event_id | 一次合成提交内的全部材料销毁行与结果入库行共用同一 event_id |
| 一场战斗结算后，对每支部队、每条实际生效并触发的时序特技各记一条（交战双方分别记录） | user_event | event_name | treasure_stunt_trigger（新增） |
| | | event_parameter | battle_id：与 user_battle 同一场战斗的 ID；node：触发节点；stunt_id；stunt_lv；影响值 effect_value：按特技类型分别为额外造成伤害/减免伤害/免疫伤害/回战士兵数/恢复士兵数；troop_role：1进攻方/2防守方；battle_result：胜/负/无胜负；rounds：本场回合数；is_real_battle：是否满足真实交战判定 |
| 真实交战胜利后授予乘胜/坚守效果时，以及该效果在连战窗口内被下一场战斗消耗或到期作废时，各记一条 | user_event | event_name | treasure_carry_effect（新增） |
| | | event_parameter | stage：1授予/2被下一场消耗/3窗口到期作废；stunt_id；stunt_lv；grant_battle_id：授予场战斗 ID；use_battle_id：生效场战斗 ID（stage=2 才有）；window_left：消耗时剩余窗口秒数 |
| 真实交战胜利产出秘宝碎片时，仅在触发保底（连续未产出达到配置场次）或当日产出已达上限时记录，正常概率产出不记录 | user_event | event_name | treasure_shard_drop（新增） |
| | | event_parameter | result：1保底产出/2达每日上限未产出；miss_battles：连续未产出的真实交战胜利场次；daily_count：当日已产出碎片数；battle_id |
| 玩家单赛季的征服金币或碎片获得量达到配置上限、后续来源被拦下时（每赛季每类上限只记一次） | user_event | event_name | treasure_supply_cap（新增） |
| | | event_parameter | cap_type：1征服金币/2碎片；season_id：KVK 赛季标识；blocked_source：被拦下的来源 1积分阶梯/2成就/3联盟礼物/4交战掉落/5每日任务；got_total：本赛季已获得总量 |
| 玩家首次满足王国纪事解锁条件、秘宝系统对其开放时 | user_event | event_name | treasure_system_unlock（新增） |
| | | event_parameter | unlock_svs：触发解锁的王国纪事节点 ID；city_level：解锁时城堡等级 |

# 待确认项

- `treasure_stunt_trigger` 的量级：按每场战斗每方每条生效特技各一条计，近 7 天 PVP 战斗约 93 万场、单方最多 4 条特技，峰值可达千万级/周。需与数据确认是全量记录、按服务器抽样，还是只记"影响值大于阈值"的触发。
- `effect_value` 的口径需与战斗程序统一：伤害类与士兵数类是两种量纲，是分列记录还是共用一列加 `effect_type` 标识。
- `is_active`（本件是否为该节点生效的那一条）由服务端在装备时算出并落日志，还是分析侧按同部队同节点的装备记录自行推导，影响是否需要该字段。
- 碎片的标准增减（获得与消耗）按框架默认写入 `user_asset`，本表未列。
  - 若数据侧需要按来源拆分碎片获得（每日任务 / 商店 / 通行证 / 掉落），需要在碎片的 `treasure_shard_add` 上追加 `reason_sub_id`，届时补一行。
- 参与型金币的阶梯发放沿用 `kvk_achievement` 还是新起 reason 未定。
  - 若沿用，需要在其 `attribute1` 补 `tier`（档位）与 `score`（达成积分）才能分析阶梯设计是否合理。
