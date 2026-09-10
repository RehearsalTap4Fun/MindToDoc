# BI 日志需求表

列名固定：日志触发逻辑 | 日志表名/类型 | 字段名 | 字段含义/取值。仅列数据分析侧需要新约定的字段，不重复标准流水字段；本功能无货币/道具增减，全部为流程节点，统一落 `user_event`。

| 日志触发逻辑 | 日志表名/类型 | 字段名 | 字段含义/取值 |
|---|---|---|---|
| 玩家对本期已发布召集的目标联盟提交入盟申请时 | user_event | event_name | recruit_cold_apply（新增） |
| | | event_parameter | from_sid：发起服；target_union_id：目标联盟ID；target_sid：目标联盟所在服；has_recommend_tag：目标是否命中推荐标签；cold_stage：当期所处阶段（预告/D1-D3/D4-D5补救） |
| 该申请审批通过、拒绝、超时失效或因目标失格自动失效时 | user_event | event_name | recruit_cold_apply_result（新增） |
| | | event_parameter | target_union_id；result：pass/refuse/expire/invalidated；fail_reason：quota_full 冷库名额已满／capacity_full 迁入额度不足／target_invalid 目标不可用／role_limit 角色数达上限／window_closed 窗口已结束／state_changed 联盟或角色状态变化（result 非 pass 时填写） |
| 盟长成功发起本期联盟迁移（界面标注【发起转移】）时 | user_event | event_name | alliance_transfer_cold_initiate（新增） |
| | | event_parameter | union_id；from_sid；target_sid；has_recommend_tag；default_carry_count：发起时默认携带人数预览 |
| 盟长取消准备中的联盟迁移时 | user_event | event_name | alliance_transfer_cold_cancel（新增） |
| | | event_parameter | union_id；from_sid；target_sid；carry_count_at_cancel：取消时的携带人数 |
| 盟长移出/恢复成员携带资格，或成员本人确认加入/退出携带名单时 | user_event | event_name | alliance_transfer_cold_member_change（新增） |
| | | event_parameter | union_id；pid：被操作成员ID；action：remove/restore/confirm/quit；operator_pid：操作者ID（成员自主操作时与 pid 相同） |
| 通道②③的联盟/个人迁移在服务器侧执行完成时（含 D3 强转，见「待确认项」） | user_event | event_name | migration_result（扩展已有：现有字段 Pid/Uid/TagSid/IsUnionApply/ApplySta/RefuseNum 见 `ctl_migration_common.go`，本次为其新增以下参数） |
| | | event_parameter | channel：alliance_transfer / personal_transfer / force_transfer；cold_source_sid：冷库来源服；has_recommend_tag |
| 预告开始时判定玩家获得当期冷库来源身份 | user_event | event_name | cold_identity_grant（新增） |
| | | event_parameter | from_sid；cold_period_id：当期召集期号或开始时间戳，用于跨事件关联同一期玩家全集 |
| D5 结束，当期冷库来源身份与未用补救机会到期 | user_event | event_name | cold_identity_expire（新增） |
| | | event_parameter | final_state：①成功/②成功/③成功/强转/未处理 |
| 通道①成功结束当期特权；②③或强转落地后获得一次①补救资格；补救资格被使用或到期作废时 | user_event | event_name | cold_privilege_change（新增） |
| | | event_parameter | change_type：consumed（特权结束）/rescue_granted（获得补救）/rescue_used（补救已用）/rescue_expired（补救到期作废）；channel：触发本次变化的通道 |
| 通道①召集入盟成功，或③/强转落地后经落地服联盟推荐入盟成功时 | user_event | event_name | union_join（扩展已有：`ctl_union_join_bi.go` 现有 `joinWay` 枚举新增取值） |
| | | event_parameter | joinWay 建议新增取值：ColdRecruitJoin（通道①入盟）、ColdLandingRecommendJoin（③/强转落地推荐入盟）——具体命名需服务端按现有 `unionJoinWay*` 系列风格核定 |
| 三通道目标列表渲染/刷新，展示当次可见的推荐目标时（曝光粒度待定，见「待确认项」） | user_event | event_name | cold_recommend_expose（新增，可选） |
| | | event_parameter | channel；target_sid_or_union_id |

# 待确认项

- **客户端点击日志**：未询问/未确认前默认不生成，上表不含 `user_click(C)`；若需要分析三通道页签的曝光-点击漏斗，请明确需要后补充。
- **强转执行方**：D3 结束的批量强转由 `game` 服务端执行还是运营平台/离线脚本执行未确认；若在 `game` 服务端且复用现有迁移完成入口，`migration_result` 的 `channel=force_transfer` 扩展即可覆盖，若由平台执行则需平台侧另行确认打点方案。
- **Reason/Event 查重**：上表全部标注「新增」的事件名为拟定命名，未能核对钉钉《X1_BI日志表说明》的 `Reason&Event&Attr说明` 枚举表（axls，当前环境无法读取），需数据部登记前二次查重去重。
- **推荐标签曝光粒度**：`cold_recommend_expose` 是否逐条上报、仅首次渲染上报、或不做曝光只在 `result` 事件的 `has_recommend_tag` 字段里体现选择结果，需数据部评估存储成本后拍板；本表暂标「新增，可选」。
- **`union_join` 新枚举值命名**：需服务端确认是否复用 `PlayerJoinUnion` 现有机制及具体取值命名。
