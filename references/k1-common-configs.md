# K1 项目公共配置表清单

> **来源**：`input/K1表格list.xlsx`（411 行表 / 页签）。  
> **范围**：本文档只列**可被多功能复用的公共配置表**与通用机制；**单活动专用表**（如 `ActivityKingdomWars` / `ActivityDragonWars` / `ActivityWarpMine` 等）不在本表内，归到该活动自己的派生文档。  
> **用途**：起新功能写 `*-配置表结构.md`「公共 / 外部依赖」时，优先从这里挑表名复用，避免重复造表。  
> **维护**：以 K1 表格 list 为准；新功能落地若发现某张活动专用表已被多处复用，再迁入本表并备注复用方。

---

## 速查（按职能找表）

| 关注点 | 主要表 / xlsx |
|--------|---------------|
| 全局常数 | `ConstConfig.xlsx` · `Config.xlsx` |
| 道具 / 货币 / 资源 | `Item.xlsx` · `VM.xlsx` · `Rss.xlsx` · `Recover.xlsx` |
| 战斗 / Buff / 技能 | `Buff.xlsx` · `BuffProperty.xlsx` · `Skill.xlsx` |
| 活动框架 / 跑马灯 / 预览 | `ActivityOnline.xlsx` |
| 通行证（多形态） | `ActivityBattlePass.xlsx` · `BattlePassChest.xlsx` · `BattlePassShop.xlsx` |
| 排行榜（活动复用） | `ActivityRank.xlsx` |
| 活动任务 | `ActivityQuest.xlsx` |
| 兑换商店 | `ExchangeShop.xlsx` |
| 礼包 / 月卡 / 周卡 | `Gift.xlsx` · `MonthlyCard.xlsx` · `FreeGift.xlsx` · `NewValuePack.xlsx` |
| 充值 | `Shop.xlsx` · `FirstRecharge.xlsx` · `FirstRechargeNew.xlsx` · `FirstRechargeList` · `ActivityRecharge.xlsx` |
| 邮件 / 推送 / 聊天 | `Mail.xlsx` · `MailModule.xlsx` · `Push.xlsx` · `ChatSystemNotification` |
| 引导 / 任务 | `Guide.xlsx` · `GoalGuide` · `NewQuest.xlsx` · `DailyQuestNew.xlsx` · `ChapterQuest.xlsx` · `Chronicle.xlsx` |
| 服务器 / 赛季 / 分组 | `ServerGroup.xlsx` · `CompetitionSeason.xlsx` |
| 客户端设置 / 适配 / 音效 / 铭牌 | `SettingAndElse.xlsx` · `GameQuality.xlsx` · `AudioList.xlsx` · `NamePlate.xlsx` · `AllianceAchievementShow.xlsx` |
| 联盟 / KVK | `Union.xlsx` · `UnionStore.xlsx` · `KvkConfig.xlsx` 等 |
| 英雄 / 兵种 / NPC | `Hero.xlsx` · `HeroEquip.xlsx` · `HeroRecruitment.xlsx` · `Evolution.xlsx` · `SoldierTalent.xlsx` · `D2NpcTroopClass.xlsx` · `NpcTroopClass.xlsx` |
| 关卡 / 主线 / 塔防 | `Stage.xlsx` · `StageChallenge.xlsx` · `Opensheet.xlsx` · `TowerDefenseMappingTable` |

---

## 一、全局基础

### 常数 / 开关

| 表 | 页签 | 用途 |
|----|------|------|
| `ConstConfig.xlsx` | `ConstConfigCfg` | 游戏全局常量（活动 `ActvSoccer_*` / 玩家改名消耗等都合并进此表） |
| `Config.xlsx` | `D2ConfigCfg` | 游戏内常数配置（与 ConstConfig 双轨） |
| `Switch.xlsx` | `D2SwitchCfg` | 开关表 |

### 道具 / 货币 / 资源 / 计数

| 表 | 页签 | 用途 |
|----|------|------|
| `Item.xlsx` | `ItemCfg` | 物品（含英雄自选卡等所有 ID） |
| `Item.xlsx` | `ItemStoreCfg` | 钻石商店 |
| `Item.xlsx` | `KingWarStoreCfg` | 国王商店 |
| `VM.xlsx` | `VmCfg` | 货币表（活动内货币也走 `vm.id`） |
| `Rss.xlsx` | `RssCfg` | 资产类型 RSS |
| `Recover.xlsx` | `RecoverCfg` | 可恢复资产 |
| `StatisticalData.xlsx` | `StatisticalDataCfg` | 计数表 |
| `Power.xlsx` | `PowerCfg` | 战力展示分类 |

### 战斗 / Buff / 技能

| 表 | 页签 | 用途 |
|----|------|------|
| `Buff.xlsx` | `BuffCfg` | buff 主表 |
| `Buff.xlsx` | `ChasingDistanceTimeCfg` | 战斗追击计算 |
| `BuffProperty.xlsx` | `BuffCategoryCfg` | Buff 多语言与属性定义 |
| `BuffProperty.xlsx` | `BuffPropertyCfg` | Buff 作用位置与多语言 |
| `Skill.xlsx` | `D2SkillCfg` / `D2EffectsCfg` / `D2ImpactBoxCfg` / `D2BulltGroupCfg` / `D2HeroPassiveSkillCfg` / `D2SkillUpgradeCfg` / `BattleBuffCfg` / `BattleSkillCfg` / `EffectListCfg` | 技能、特效、伤害盒、英雄被动、技能组、兵种技能 |

### 关卡 / 主线 / 塔防

| 表 | 页签 | 用途 |
|----|------|------|
| `Stage.xlsx` | `D2StageCfg` | 关卡配置 |
| `Stage.xlsx` | `EventsCfg` | 塔防内随机礼物弹窗 |
| `StageChallenge.xlsx` | `StageChallengeCfg` | 关卡挑战赛 |
| `Opensheet.xlsx` | `D2OpensheetCfg` | 塔防玩法 |
| `TowerDefenseMappingTable` | `TowerDefenseMappingTableCfg` | 肉鸽塔防与老塔防关卡映射 |
| `Tech.xlsx` | `D2TechCfg` | 主城升级 / 科技 |
| `CityBuilding.xlsx` | `D2CityBuildingCfg` | 主城内每个建筑解锁关卡数 |
| `Dragon.xlsx` | `D2DragonCfg` / `D2NewDragonCfg` / `DragonEggCfg` | 龙形态 / 龙纹石 / 主线表现 |
| `DragonEquip.xlsx` | `DragonEquipCfg` | 龙装备 |
| `DragonStageMatchNew` | `NewDraStageCfg` | 本服巨龙战场 |

### 英雄 / 兵种 / NPC

| 表 | 页签 | 用途 |
|----|------|------|
| `Hero.xlsx` | `D2HeroCfg` / `D2HeroAttributeCfg` / `D2HeroExpCfg` / `HeroBondCfg` / `HeroRelationCfg` | 英雄列表 / 升级 / 经验 / 羁绊 |
| `HeroEquip.xlsx` | `HeroEquipCfg` / `BlackSmithCfg` | 英雄装备 / 铁匠铺 |
| `HeroRecruitment.xlsx` | `HeroRecruitmentCfg` / `HeroRecruimentGroupCfg` / `MonthHeroCfg` | 英雄招募 / 抽卡 / 每月条 |
| `Evolution.xlsx` | `D2EvolutionCfg` / `D2EvolutionUpgradePowerCfg` | 士兵进阶 / 等级 |
| `SoldierTalent.xlsx` | `SoldierTalentCfg` / `SoldierTalentReturnCfg` | 士兵天赋 / 返还 |
| `D2NpcTroopClass.xlsx` | `D2NpcTroopClassCfg` | 怪物刷新属性 |
| `NpcTroopClass.xlsx` | `D2NpcBandCfg` / `D2NpcZoneCfg` / `D2SearchCfg` / `D2SoldierCfg` / `SoldierCfg` / `NpcMoveCfg` / `NpcMovePointCfg` / `NpcTroopPowerCfg` | 怪物刷新 / 建筑刷新 / 状态提示 / 地图对象 / 士兵战力 / NPC 移动 |
| `Monster.xlsx` | `D2MonsterCfg` / `D2MonsterHPCfg` | Boss 图鉴 |
| `MarchType.xlsx` | `MarchTypeCfg` | 行军类型 |
| `Horde` | `HordeCfg` | 阵营识别 |
| `AISystem.xlsx` | `AIPowerCfg` / `AIBasicCfg` / `AIAllianceBasicCfg` | AI 机器人战力 / 信息 / AI 联盟 |

---

## 二、活动通用配套（写新活动优先复用）

### 活动框架

| 表 | 页签 | 用途 |
|----|------|------|
| `ActivityOnline.xlsx` | `ActvOnlineCfg` | **活动表**（限时开关、活动 ID） |
| `ActivityOnline.xlsx` | `PreviewShowCfg` | 节日活动预览页 |
| `ActivityOnline.xlsx` | `BroadcastCfg` | 跑马灯 / 聊天通告 |

### 通行证（多形态共三套）

| 表 | 页签 | 用途 |
|----|------|------|
| `ActivityBattlePass.xlsx` | `ActvBattlePassCfg` / `ActvBattlePassSectionCfg` | 通用通行证 + 奖励档位 |
| `BattlePassChest.xlsx` | `BattlePassChestCfg` / `BPChestRewardCfg` / `BPChestTaskCfg` / `BPChestOpenCfg` | 充值宝箱式通行证 |
| `BattlePassShop.xlsx` | `BPShopGiftCfg` / `BPShopRewardCfg` / `BPShopTaskCfg` / `BPShopCfg` | 折扣商店式通行证 |

### 排行榜

| 表 | 页签 | 用途 |
|----|------|------|
| `ActivityRank.xlsx` | `ActvRankCfg` | 排行榜打组 |
| `ActivityRank.xlsx` | `ActvRankSectionCfg` | 排行榜段位档位 |

### 活动任务

| 表 | 页签 | 用途 |
|----|------|------|
| `ActivityQuest.xlsx` | `ActvQuestCfg` | 女巫 / 集结 / 打野 / 登录等活动任务 |
| `ActivityQuest.xlsx` | `ActvQuestTypeCfg` | 活动任务分组 |

### 兑换商店

| 表 | 页签 | 用途 |
|----|------|------|
| `ExchangeShop.xlsx` | `D2ExchangeShopItemCfg` | 白金兑换商店 - 道具 |
| `ExchangeShop.xlsx` | `D2ExchangeShopFrameCfg` | 头像框兑换 |
| `ExchangeShop.xlsx` | `D2ExchangeShopSkinCfg` | 城堡皮肤兑换 |
| `ExchangeShop.xlsx` | `D2ExchangeShopNamePlateCfg` | 铭牌兑换 |

### 礼包 / 月卡 / 周卡 / 超值

| 表 | 页签 | 用途 |
|----|------|------|
| `Gift.xlsx` | `D2GiftCfg` | 礼包基础属性主表 |
| `Gift.xlsx` | `D2GNewLabelCfg` / `D2GNewDailyCfg` / `D2GiftLabelCfg` | 特惠页签 / 每日特购 / 活动开关 |
| `Gift.xlsx` | `D2GiftSkinImgCfg` / `D2GiftPriceCfg` | 城堡兑换页 / 钻石购买商城 |
| `Gift.xlsx` | `WeeklyCardCfg` | 周卡 |
| `Gift.xlsx` | `ThemeSpecialPackCfg` / `ThemeSpecialPackIconCfg` | 每日定制一口价礼包 |
| `Gift.xlsx` | `DeleteGiftPackSuppementCfg` | 礼包表找不到的 ID 兜底 |
| `MonthlyCard.xlsx` | `D2MonthCardCfg` / `D2MonthCardPropertyCfg` | 月卡 |
| `FreeGift.xlsx` | `FreeRewardcfg` | 免费礼包 |
| `NewValuePack.xlsx` | `NewValuePackCfg` / `NewValueFreePackCfg` | 超值礼包进度奖 |
| `ActivityOptionalPack.xlsx` | `ActvOptionalPackCfg` | 自选礼包 |

### 充值

| 表 | 页签 | 用途 |
|----|------|------|
| `Shop.xlsx` | `D2ShopCfg` / `D2PowerBuyCfg` | 充值商店 / 体力 |
| `FirstRecharge.xlsx` | `FirstRechargeCfg` | 首冲后续领取 |
| `FirstRechargeNew.xlsx` | `FirstRechargeNewCfg` | 首冲三选一（区分国家） |
| `FirstRechargeList` | `FirstRechargeVersionListCfg` / `FirstRechargeGroup1Cfg` | 新首充版本 / 分组 |
| `ActivityRecharge.xlsx` | `ActvRechargeCfg` / `ActvRechargeTypeCfg` | 累计充值 + 排行 / 重置 |
| `ActivityRecharge.xlsx` | `ActvAllianceTreasureCfg` | 个人 / 联盟充值活动 |
| `ActivityRecharge.xlsx` | `ActvPaymentCfg` | 单笔充值奖励 |
| `ActivityRecharge.xlsx` | `ActvGuardRechargeCfg` | 守卫币累计充值 |
| `GrowthFund.xlsx` | `D2GrowthFundCfg` / `D2GrowthFundGroupCfg` | 成长基金 |
| `GrowthFund.xlsx` | `BankCfg` | 银行（特惠页签） |
| `GrowthFund.xlsx` | `CalenderRewardCfg` / `CalenderGiftCfg` | 养成线日历 |
| `GrowthFund.xlsx` | `OnlineRewardCfg` | 在线 / 龙宝箱奖励 |
| `ADshop.xlsx` | `ADShopCfg` / `ADShopGroupCfg` | 广告商城 |

---

## 三、玩家系统通用

### 邮件 / 推送 / 聊天

| 表 | 页签 | 用途 |
|----|------|------|
| `Mail.xlsx` | `MailCfg` | 老邮件 |
| `Mail.xlsx` | `MailBoxCfg` | 新邮件 |
| `Mail.xlsx` | `NewMailCfg` | 邮件组 |
| `MailModule.xlsx` | `MailModuleCfg` | 邮件模块 |
| `Push.xlsx` | `D2PushCfg` / `D2BundleListCfg` | 推送 / 平台 |
| `ChatSystemNotification` | — | 聊天事件通知 |

### 引导 / 任务 / 章节 / 纪事

| 表 | 页签 | 用途 |
|----|------|------|
| `Guide.xlsx` | `D2GuideCfg` / `D2NewGuideCfg` | 前期合成引导 / 新引导 |
| `Guide.xlsx` | `AiGuideCfg` | AI 触发引导 |
| `GoalGuide` | `GoalGuideListCfg` / `GoalGuideConCfg` | 目标引导 |
| `NewQuest.xlsx` | `MainQuestCfg` / `AchievementQuestCfg` / `QuestListCfg` | 主线 / 成就 / 任务列表 |
| `DailyQuestNew.xlsx` | `NewQuestCommonCfg` / `NewQuestChestCfg` / `QuestTypeCfg` | 新版每日任务 / 每周大宝箱 / 任务类型 |
| `ChapterQuest.xlsx` | `ChapterQuestCfg` / `ChapterRewardCfg` | 章节任务 / 章节节点 |
| `Chronicle.xlsx` | `ChronicleCfg` / `ChronicleRewardCfg` / `EventCfg` | 王国纪事 / 阶段排名 / 解锁事件 |
| `BountyTask.xlsx` | `BountyTaskListCfg` | 赏金工会悬赏任务 |
| `LittleGameAchievement.xlsx` | `LittleGameAchievementCfg` / `BundleIdCfg` | CPE 点位 |
| `PraiseGuide` | `PriseGuideCfg` / `SurveyLinkCfg` | 问卷 / 新人问卷 |

### VIP / 累计奖励 / 版本

| 表 | 页签 | 用途 |
|----|------|------|
| `VIP.xlsx` | `VipInfoCfg` / `VipStoreCfg` / `VipPropertyCfg` | VIP 权限 / 商店 / 属性 |
| `ReservationReward.xlsx` | `ReservationRewardCfg` | 累计注册人数奖励 |
| `VersionReward` | `VersionRewardCfg` | 版本奖励 |
| `ShareActv.xlsx` | `ShareActvCfg` | 分享奖励 |
| `ShareIcon.xlsx` | `ShareIconCfg` | 分享 - 建筑分享图标 |

### 客户端设置 / 适配 / 音效 / 铭牌 / 头像

| 表 | 页签 | 用途 |
|----|------|------|
| `SettingAndElse.xlsx` | `BadWordCfg` | 屏蔽词 |
| `SettingAndElse.xlsx` | `ServiceHideCfg` | 客服入口 |
| `SettingAndElse.xlsx` | `LanguageListCfg` | 语言设置 |
| `SettingAndElse.xlsx` | `PlayerAvatarCfg` | 角色形象 |
| `SettingAndElse.xlsx` | `D2TripartiteActivitiesCfg` | 社交平台跳转 |
| `SettingAndElse.xlsx` | `D2UnlockSkinCfg` | 内城场景 |
| `SettingAndElse.xlsx` | `NewRallyCfg` | 战力菜单显示 |
| `SettingAndElse.xlsx` | `PlayerDataCfg` | 角色信息 |
| `GameQuality.xlsx` | `GameQualitySettingsGenericCfg` / `GameQualitySettingsIosCfg` / `GameQualitySettingsProfileCfg` | 安卓 / IOS 机型适配 / 输出 Profile |
| `AudioList.xlsx` | `AudioListCfg` | 音效文件属性 |
| `NamePlate.xlsx` | `NamePlateCfg` / `NamePlateGroupCfg` / `NamePlatePropertyCfg` | 铭牌主表 / 分组 / 属性 |
| `AllianceAchievementShow.xlsx` | `AchievementShowCfg` / `PrivateShowCfg` | 联盟 / 个人成就炫耀 |
| `Sence.xlsx` | `D2SenceCfg` / `D2NormalSkinCfg` / `D2SencePropertyCfg` / `AvatarFrameNewCfg` / `AvatarFramePropertyCfg` | 城堡皮肤 / 外观 / 头像框（显示+Buff） |

### 服务器 / 赛季 / 跨服

| 表 | 页签 | 用途 |
|----|------|------|
| `ServerGroup.xlsx` | `ServerGroupCfg` / `EventGroupCfg` / `ColdServerCfg` | 服务器分组 / 活动分组 / 冷库服 |
| `CompetitionSeason.xlsx` | `SeasonCfg` / `SeasonGroupCfg` / `SeasonRankCfg` / `SeasonRewardCfg` / `SeasonRecruitCfg` | 赛季城堡/泰坦上限 / 服表 / 排行 / 国王邮件 / 赛季抽奖 |
| `KvkConfig.xlsx` | `KvkConfigCfg` | KVK 功能设置 |
| `KvkEve.xlsx` | `KvkEveContentCfg` / `KvkEveQuestCfg` / `KvkEveScoreCfg` | KVK 前置预告 |
| `KvkQuest.xlsx` | `KvkQuestCfg` / `KvkQuestTypeCfg` / `ActvKingdomWarsShopCfg` / `ActvKingdomWarsShopShelfCfg` | KVK 任务 / 类型 / 商店 / 解锁 |
| `KvkTech.xlsx` | `KvkTechCfg` | KVK 科技 |
| `KvkDonate.xlsx` | `KvkDonateCfg` | 世界树捐献 |
| `KvkCrystalBattlePass.xlsx` | `KvkCrystalRewardCfg` / `KvkCrystalTaskCfg` / `KvkCrystalCardCfg` | KVK 水晶战票 |

### 联盟

| 表 | 页签 | 用途 |
|----|------|------|
| `Union.xlsx` | `UnionClassCfg` / `UnionClassDetailCfg` | 联盟权限 |
| `Union.xlsx` | `UnionGiftCfg` / `UnionChestCfg` | 联盟礼物宝箱 |
| `Union.xlsx` | `MobilizationCommonCfg` / `MobilizationRankCfg` / `MobilizationMilestoneCfg` | 联盟挑战 / 奖励 / 排行 |
| `Union.xlsx` | `UnionTechCfg` / `UnionTechListCfg` | 联盟科技 |
| `Union.xlsx` | `UnionLevelCfg` | 联盟升级 |
| `Union.xlsx` | `UnionTerritoryCfg` / `UnionTerritoryPropertyCfg` | 联盟领地 |
| `Union.xlsx` | `UnionWarBuildingCfg` / `UnionWarBuildingPropertyCfg` | 圣坛 / 龙巢 / 地图建筑属性 |
| `Union.xlsx` | `StageLavaCaveCfg` / `LavaCaveItemCfg` / `LavaCaveMapCfg` | 联盟熔岩洞穴 |
| `Union.xlsx` | `NewAllianceGroupCfg` / `NewAllianceQuestCfg` / `NewAlliancePrivateQuestCfg` / `AllianceHelpRewardCfg` | 联盟成就 |
| `UnionStore.xlsx` | `UnionStoreShelfCfg` / `UnionStoreItemCfg` | 联盟商店 |

### 神器 / 秘宝 / 女巫 / 召唤兽

| 表 | 页签 | 用途 |
|----|------|------|
| `Artifacts.xlsx` | `ArtifactsCfg` | 神器装备 |
| `Treasure.xlsx` | `TreasureItemCfg` / `AttributeCfg` / `StuntCfg` | 秘宝 / 属性 / 绝技 |
| `WitchLab.xlsx` | `WitchLabCfg` | 女巫升级 |
| `WitchStone.xlsx` | `WitchStoneCfg` | 女巫宝石 / 魔女实验室 |
| `SummonAltar.xlsx` | `SummonAltarCfg` | 召唤兽 |

### 地图 / 模型

| 表 | 页签 | 用途 |
|----|------|------|
| `MapSize.xlsx` | `MapSizeCfg` / `MapTypeCfg` | 地图尺寸 / 类型 |
| `Model.xlsx` | `D2ModelCfg` | 模型表 |
| `IntuitiveZoom.xlsx` | `IntuitiveZoomCfg` / `D2MapUnitGroupCfg` / `TroopFormationCfg` / `SpecialTroopCfg` | 地图层级显示 / 分组 / 部队 / 部队移动速度 |
| `DayNight.xlsx` | `DayNightCfg` | 昼夜切换 |
| `NationFlag` | `NationFlagCfg` | 导量策略 |

### 情报站 / 次元矿洞 / 试炼 / 国王战 / 资源

| 表 | 页签 | 用途 |
|----|------|------|
| `EnergyAtlas.xlsx` | `EnergyAtlasCfg` / `EnergyAtlasMissionCfg` / `EnergyAtlasGourpCfg` / `EnergyAtlasLevelCfg` | 情报站 |
| `DimensionTreasure.xlsx` | `DimensionTreasureCfg` / `DimensionShopCfg` / `DimensionQuestCfg` | 次元矿洞 |
| `GoddessTrialList.xlsx` | `GoddessTrialListCfg` / `GoddessTrialStageCfg` / `GoddessTrialUnlockCfg` / `GoddessTrialShopCfg` | 女神的试炼 |
| `KingWar.xlsx` | `KingWarGiftCfg` / `KingWarBuildingCfg` / `KingWarPositionCfg` / `KingWarRrewardCfg` / `KingWarScoreRewardCfg` / `KingWarSkillsCfg` / `NewBuffCfg` | 王座战 |
| `D2Gather.xlsx` | `D2GatherCfg` / `OfflineRevenueCfg` | 金矿产量 / 离线 / 资源矿 |
| `AssetAlarm.xlsx` | `AssetAlarmCfg` / `ResourceAlarmCfg` | 服务器道具阈值报警 |

### 拆表 / 通用辅助

| 表 | 页签 | 用途 |
|----|------|------|
| `split_tables` | — | 奖励表拆表 |
| `Tips.xlsx` | `D2ProbabilityTipsIconCfg` / `D2ProbabilityTipsDetailCfg` / `D2ProbabilityTipsTotalCfg` | 概率提示 |
| `PowerCompare.xlsx` | `PowerCompareCfg` | 战力比较 |

---

## 四、通用 proto / 机制（不在 xlsx，但策划填表必引用）

| 类型 | 引用 | 何处使用 |
|------|------|----------|
| 奖励结构 | `TypIDVal_P_cspb` | 任意表 `Reward` / `SeasonReward` / `SignReward` / `FreeReward` / `PaidReward` 等 `ext[]` |
| 坐标 / 向量 | `PositionTuple_P` | 通用位置 / 方向字段 |
| 全局邮件 | 全局邮件模块 | 离线派彩 / 排名发奖 / 补偿 |
| 多语言 | 项目语言表（K1 用功能名前缀，如 `ActvSoccer_`） | 业务表只写 key，中文进对应语言表 |
| 货币 | 项目通用货币体系 → `VM.xlsx` | 活动 xlsx 不维护货币类型，业务表通过 `vm.id` 间接引用 |
| 物品 | 项目通用物品体系 → `Item.xlsx` | 引用已有物品 ID |

---

## 五、使用约定

1. **写新功能配置表派生时**，先在本表对照「公共 / 外部依赖」一栏；命中即用，**不复制粘贴本表内容到派生文档**，写一行「本功能用 X 走 `Item.xlsx / ItemCfg`，详见 `references/k1-common-configs.md`」。
2. **不属于上面任何一类的活动专用表**（如 `ActivitySoccer*` / `ActivityKingdomWars*` / `ActivityDragonWars*`），写在该活动自己的派生文档，不进本表。
3. **本文档以 `input/K1表格list.xlsx` 为底**；新增功能落地后若发现某通用表漏录，按所在分类追加；废弃表标 ~~删除线~~ + 备注废弃版本，不直接删行。
4. **找不到合适的公共表**才考虑新建；新建前先和数值 / 程序对齐是否可挂在已有公共表的页签下。
