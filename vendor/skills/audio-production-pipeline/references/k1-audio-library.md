# K1 项目组音效复用库

来源：`AudioListCfg.tsv`、`AudioConst.cs` 注释、仓库内 `.wav/.ogg/.mp3` 文件名。

## 使用规则

- K1 项目拆音效需求前，先查本库；命中同类语义时，标注 `复用`，资源名填已有 ID 或文件名。
- 常规 UI 反馈、奖励领取、宝箱卡牌、升级解锁、错误提示、地图行军、BGM/环境音优先复用。
- 活动玩法、角色技能、强主题包装音效只有在现有语义不贴合时才标注 `新增`。
- 表格没有独立备注列时，以 `AudioConst` 注释和文件名语义作为复用判断依据；最终需要人工试听确认。

## 资源概况

- 配表：`k1_client/client/Assets/Res/config/AudioListCfg.tsv`
- 配表条目：717
- 扫描到音频文件：765
- 配表资源未在本地文件名中直接命中：17
- 类型统计 `C_INT_typ`：{'0': 495, '1': 41, '3': 7, '2': 142, '4': 32}
- 场景统计 `C_INT_scene`：{'1': 320, '0': 171, '4': 1, '2': 16, '3': 38, '5': 145, '6': 22, '7': 4}

## 常用复用入口

### 通用按钮点击

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `15220030` | `UI_generic.ogg` | MapUnitClick | `0` | `0` |
| `15220034` | `UI_i_generic.ogg` | UIGeneric: 通用UI点击音效 | `0` | `0` |
| `15220089` | `UI_confirm_button_click.ogg` | - | `0` | `0` |
| `15220013` | `UI_generic.ogg` | LaunchMarch | `3` | `0` |
| `15220027` | `UI_chest.wav` | LineUpClick | `0` | `0` |
| `15220031` | `UI_h_button1.wav` | - | `0` | `0` |
| `15220032` | `UI_h_button2.ogg` | - | `0` | `0` |
| `15220033` | `UI_h_button3.ogg` | CityChange | `0` | `0` |
| `15220080` | `UI_button_bag.ogg` | - | `0` | `0` |
| `15220081` | `UI_button_chat.ogg` | - | `0` | `0` |

### 关闭/返回按钮

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `15220022` | `Map_trh.ogg` | TroopsReturn | `3` | `0` |
| `15220026` | `UI_back.ogg` | - | `0` | `0` |
| `15220029` | `UI_close.ogg` | SearchClose | `0` | `0` |
| `15220070` | `Sound_UI_window_close.wav` | - | `0` | `0` |
| `20` | `Sound_Scene_Close.ogg` | SOUND_SCENE_CLOSE: 关门音效 | `0` | `0` |
| `27` | `Menu_close.ogg` | BGSOUND_UI_MENU_CLOSE: 主界面菜单关闭音效 | `0` | `0` |

### 普通弹窗打开/关闭

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `15220029` | `UI_close.ogg` | SearchClose | `0` | `0` |
| `15220070` | `Sound_UI_window_close.wav` | - | `0` | `0` |
| `15220071` | `Sound_UI_window_open.wav` | - | `0` | `0` |
| `15220076` | `Chest_metal_appear.ogg` | MetalBoxOpen | `0` | `0` |
| `15220077` | `Chest_wood_appear.ogg` | WoodBoxOpen | `0` | `0` |
| `15220096` | `UI_popup_ad.ogg` | - | `0` | `0` |
| `190000001` | `UI_envelope_popup.wav` | - | `0` | `0` |
| `190000002` | `UI_envelope_open.wav` | - | `0` | `0` |
| `20` | `Sound_Scene_Close.ogg` | SOUND_SCENE_CLOSE: 关门音效 | `0` | `0` |
| `22000005` | `mus_opening_cg.wav` | - | `0` | `1` |

### 页签/横向切换/选中

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `15220087` | `UI_click_label.ogg` | - | `0` | `0` |
| `15220109` | `map_click_troop.ogg` | WorldSelectTroops | `3` | `0` |
| `24000103` | `roguelike_tower_ui_card_select.ogg` | - | `0` | `2` |
| `28` | `Switch_scene.ogg` | - | `0` | `0` |

### 领取/获得奖励

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `53` | `UI_quest_reward_coin_collected.wav` | COIN_FLY | `0` | `2` |
| `15220005` | `C_collect.ogg` | CollectRss | `0` | `0` |
| `15220028` | `UI_claim.ogg` | Claim | `0` | `0` |
| `22000024` | `halloween_slot_reward_popup.ogg` | UI_ACTIVITY_SLOTMACHINE_REWARD_POPUP: 老虎机奖励弹窗 | `0` | `0` |
| `22100002` | `kingdom_treasure_reward_popup.ogg` | - | `0` | `0` |
| `22200004` | `forest_treasure_reward.wav` | forest_treasure_reward: 点击龟壳破裂时音效 | `6` | `0` |
| `22200014` | `forest_treasure_collect_timespring.wav` | forest_treasure_collect_timespring: 时间泉水使用音效 | `6` | `0` |
| `22200015` | `forest_treasure_collect_sunstone.wav` | forest_treasure_collect_sunstone: 资源收集-太阳石音效 | `6` | `0` |
| `22200016` | `forest_treasure_collect_key.wav` | forest_treasure_collect_key: 资源收集-钥匙音效 | `6` | `0` |
| `22200017` | `forest_treasure_collect_crown.wav` | forest_treasure_collect_crown: 资源收集-皇冠音效 | `6` | `0` |

### 宝箱/卡牌表现

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `60` | `Chest_wood_jump.ogg` | SOUND_UI_DRAW_CARD_JUMP_WOOD: 木箱：点击已开箱的箱子弹跳的动画 | `0` | `0` |
| `61` | `Chest_metal_appear.ogg` | SOUND_UI_DRAW_CARD_JUMP_FIRST: 铁箱：第一次跳出并开箱的动画 | `0` | `0` |
| `62` | `Chest_metal_jump.ogg` | SOUND_UI_DRAW_CARD_JUMP: 铁箱：点击已开箱的箱子弹跳的动画 | `0` | `0` |
| `63` | `Receive_cards_all.ogg` | SOUND_UI_AGAIN_DRAW_CARD_TEN_TIMES: 再次点击，十连抽的时候 | `0` | `0` |
| `15220027` | `UI_chest.wav` | LineUpClick | `0` | `0` |
| `15220076` | `Chest_metal_appear.ogg` | MetalBoxOpen | `0` | `0` |
| `15220077` | `Chest_wood_appear.ogg` | WoodBoxOpen | `0` | `0` |
| `22000035` | `collapse_click_card.wav` | - | `0` | `0` |
| `22000036` | `collapse_card_in_place.wav` | - | `0` | `0` |
| `22000037` | `collapse_card_clear_up.wav` | - | `0` | `0` |

### 升级/解锁/成功反馈

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `15220075` | `SFX_hero_levelup.wav` | HeroLvUpAndStarUp | `0` | `0` |
| `34` | `Sound_Scene_LevelUp.wav` | SOUND_UI_BAR_UPGRADE1: 进度条1 | `0` | `0` |
| `35` | `Sound_Scene_Success.wav` | SOUND_UI_BAR_UPGRADE2: 进度条2 | `0` | `0` |
| `15220002` | `C_c_levelup.wav` | - | `0` | `2` |
| `15220007` | `C_levelup.wav` | - | `0` | `0` |
| `15220016` | `Map_r_starts.ogg` | RallyStart | `3` | `0` |
| `15220068` | `Sound_UI_soldier_levelup.wav` | - | `0` | `0` |
| `15220069` | `Sound_UI_soldier_talent_levelup.wav` | - | `0` | `0` |
| `190000003` | `ui_upgrade_effect_small.wav` | - | `0` | `0` |
| `190000004` | `ui_upgrade_effect_big.wav` | - | `0` | `0` |

### 错误/不可点击反馈

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `21` | `Sound_Scene_BuyError.wav` | SOUND_SCENE_BUYERROR: 金币不足购买 | `0` | `0` |
| `15220036` | `UI_negative.wav` | - | `0` | `0` |
| `17` | `Sound_Scene_Error.wav` | SOUND_SCENE_ERROR: 合成区满的音效 | `0` | `0` |
| `19` | `Sound_Scene_Comerror.wav` | - | `0` | `0` |
| `22000034` | `capybara_game_lock_capybara.wav` | - | `0` | `0` |
| `3` | `Sound_Scene_Unlock.wav` | SOUND_UI_UNLOCK: 解锁音效 | `0` | `0` |

### 金币/道具飞入或增长

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `37` | `Increase_coin.ogg` | BGSOUND_UI_ITEM: 物品背景音效 | `0` | `0` |
| `53` | `UI_quest_reward_coin_collected.wav` | COIN_FLY | `0` | `2` |
| `54` | `ui_diamond_in_2.ogg` | DIAMOND_FLY | `0` | `2` |
| `55` | `UI_item.ogg` | ITEM_FLY | `0` | `0` |
| `15220035` | `UI_item.ogg` | - | `0` | `0` |
| `15220085` | `UI_click_coin.ogg` | - | `0` | `0` |
| `22200018` | `forest_treasure_collect_coin.wav` | forest_treasure_collect_coin: 资源收集-琥珀音效 | `6` | `0` |
| `36` | `Sound_UI_Win.wav` | BGSOUND_UI_COIN: 金钱背景音效 | `0` | `0` |
| `38` | `Increase_exp.ogg` | BGSOUND_UI_HERO: 英雄背景音效 | `0` | `0` |
| `59` | `Receive_card_single.ogg` | SOUND_UI_CARD_FLY: 卡牌飞出（所有箱子通用） | `0` | `0` |

### 地图点击/行军/传送

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `15220015` | `Map_r_creation.ogg` | LaunchRally | `3` | `0` |
| `15220016` | `Map_r_starts.ogg` | RallyStart | `3` | `0` |
| `15220017` | `Map_shieldon.ogg` | CityShieldOn | `3` | `0` |
| `15220021` | `Map_teleport.ogg` | - | `3` | `0` |
| `15220022` | `Map_trh.ogg` | TroopsReturn | `3` | `0` |
| `15220047` | `K1-WorldMap-War-loop.wav` | RallyAttack | `3` | `1` |
| `15220109` | `map_click_troop.ogg` | WorldSelectTroops | `3` | `0` |
| `15220006` | `C_h_troops.wav` | - | `0` | `0` |
| `15220012` | `Map_crd.ogg` | - | `3` | `0` |
| `15220013` | `UI_generic.ogg` | LaunchMarch | `3` | `0` |

### 循环环境/BGM

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `56` | `amb_city.ogg` | CITY_BUILDING_AMBIENT_BGM: 内城城建环境背景音 | `2` | `1` |
| `57` | `amb_map.ogg` | WORLD_AMBIENT_BGM: 大世界环境背景音 | `3` | `1` |
| `15220041` | `CivilizedAmbiance_4.ogg` | - | `0` | `1` |
| `15220043` | `ApesTavernLoop.wav` | - | `0` | `0` |
| `15220044` | `FTEIntroMusic.wav` | - | `0` | `0` |
| `15220045` | `FTESFXmusic.wav` | - | `0` | `0` |
| `15220047` | `K1-WorldMap-War-loop.wav` | RallyAttack | `3` | `1` |
| `15220072` | `mus_map_day.ogg` | WORLD_DAY_BGM: 大地图白天时背景音 | `3` | `1` |
| `15220073` | `mus_map_night.ogg` | WORLD_NIGHT_BGM: 大地图夜晚时背景音 | `3` | `1` |
| `21000002` | `Artifacts_Loop.wav` | - | `0` | `0` |

## 分类索引

### UI通用点击/按钮

共 23 条。优先检索关键词：`generic`, `button`, `click`, `btn`, `ui_i_generic`, `ui_h_button`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `15220013` | `UI_generic.ogg` | LaunchMarch | `3` | `0` |
| `15220027` | `UI_chest.wav` | LineUpClick | `0` | `0` |
| `15220030` | `UI_generic.ogg` | MapUnitClick | `0` | `0` |
| `15220031` | `UI_h_button1.wav` | - | `0` | `0` |
| `15220032` | `UI_h_button2.ogg` | - | `0` | `0` |
| `15220033` | `UI_h_button3.ogg` | CityChange | `0` | `0` |
| `15220034` | `UI_i_generic.ogg` | UIGeneric: 通用UI点击音效 | `0` | `0` |
| `15220080` | `UI_button_bag.ogg` | - | `0` | `0` |
| `15220081` | `UI_button_chat.ogg` | - | `0` | `0` |
| `15220082` | `UI_button_mail.ogg` | - | `0` | `0` |
| `15220083` | `UI_button_mission.ogg` | - | `0` | `0` |
| `15220084` | `UI_button_ranking.ogg` | - | `0` | `0` |
| `15220085` | `UI_click_coin.ogg` | - | `0` | `0` |
| `15220086` | `UI_click_gem.ogg` | - | `0` | `0` |
| `15220087` | `UI_click_label.ogg` | - | `0` | `0` |
| `15220089` | `UI_confirm_button_click.ogg` | - | `0` | `0` |
| `15220097` | `UI_rank_badge_click.ogg` | - | `0` | `0` |
| `15220098` | `UI_tab_hor_click.ogg` | - | `0` | `0` |
| `15220099` | `UI_toolbar_click.ogg` | - | `0` | `0` |
| `15220108` | `UI_longclick.ogg` | WorldLongClick | `3` | `0` |
| `15220109` | `map_click_troop.ogg` | WorldSelectTroops | `3` | `0` |
| `22000021` | `halloween_slot_button_start.ogg` | UI_ACTIVITY_SLOTMACHINE_BUTTON_START: 老虎机按下开始按钮 | `0` | `0` |
| `22000035` | `collapse_click_card.wav` | - | `0` | `0` |

### UI关闭/返回

共 6 条。优先检索关键词：`close`, `back`, `return`, `menu_close`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `20` | `Sound_Scene_Close.ogg` | SOUND_SCENE_CLOSE: 关门音效 | `0` | `0` |
| `27` | `Menu_close.ogg` | BGSOUND_UI_MENU_CLOSE: 主界面菜单关闭音效 | `0` | `0` |
| `15220022` | `Map_trh.ogg` | TroopsReturn | `3` | `0` |
| `15220026` | `UI_back.ogg` | - | `0` | `0` |
| `15220029` | `UI_close.ogg` | SearchClose | `0` | `0` |
| `15220070` | `Sound_UI_window_close.wav` | - | `0` | `0` |

### UI打开/弹窗/出现

共 25 条。优先检索关键词：`popup`, `appear`, `open`, `show`, `menu_open`, `envelope_popup`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `7` | `Sound_Scene_Open.ogg` | SOUND_SCENE_OPEN: 开门音效 | `1` | `0` |
| `26` | `Menu_open.ogg` | BGSOUND_UI_MENU_OPEN: 主界面菜单开启音效 | `0` | `0` |
| `30` | `Sound_UI_Chest_open.wav` | SOUND_UI_CHEST_OPEN: 宝箱崩一下 | `0` | `0` |
| `31` | `Sound_UI_Chest_open_01.wav` | SOUND_UI_CHEST_OPEN1: 宝箱原地崩 | `0` | `0` |
| `33` | `Card_show.ogg` | SOUND_UI_CARD_SHOW: 卡牌展示 | `0` | `0` |
| `58` | `Chest_wood_appear.ogg` | SOUND_UI_WOOD_CHEST_OPEN: 木箱：第一次跳出并开箱的动画 | `0` | `0` |
| `61` | `Chest_metal_appear.ogg` | SOUND_UI_DRAW_CARD_JUMP_FIRST: 铁箱：第一次跳出并开箱的动画 | `0` | `0` |
| `15220071` | `Sound_UI_window_open.wav` | - | `0` | `0` |
| `15220076` | `Chest_metal_appear.ogg` | MetalBoxOpen | `0` | `0` |
| `15220077` | `Chest_wood_appear.ogg` | WoodBoxOpen | `0` | `0` |
| `15220096` | `UI_popup_ad.ogg` | - | `0` | `0` |
| `15220118` | `Sound_City_arena.wav` | AreaShowAudio | `2` | `0` |
| `15220119` | `Sound_City_forge.wav` | EquioShowAudio | `2` | `0` |
| `15220120` | `Sound_City_kinghall.wav` | KingHallShowAudio | `2` | `0` |
| `15220121` | `Sound_City_lab.wav` | WitchShowAudio | `2` | `0` |
| `15220122` | `Sound_City_summon.wav` | SummonShowAudio | `2` | `0` |
| `15220123` | `Sound_City_teleport.wav` | TreasureShowAudio | `2` | `0` |
| `22000005` | `mus_opening_cg.wav` | - | `0` | `1` |
| `22000024` | `halloween_slot_reward_popup.ogg` | UI_ACTIVITY_SLOTMACHINE_REWARD_POPUP: 老虎机奖励弹窗 | `0` | `0` |
| `22100001` | `kingdom_treasure_vine_appear.ogg` | - | `0` | `0` |
| `22100002` | `kingdom_treasure_reward_popup.ogg` | - | `0` | `0` |
| `24000102` | `roguelike_tower_ui_card_popup.ogg` | - | `0` | `2` |
| `26000006` | `Sound_Ui_Kingopoly_Trigger_Event_Appear.ogg` | - | `0` | `1` |
| `190000001` | `UI_envelope_popup.wav` | - | `0` | `0` |
| `190000002` | `UI_envelope_open.wav` | - | `0` | `0` |

### UI切换/选中/列表

共 3 条。优先检索关键词：`tab`, `switch`, `select`, `label`, `lable`, `horizontal`, `ruler`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `28` | `Switch_scene.ogg` | - | `0` | `0` |
| `15220038` | `UI_ruler.wav` | - | `0` | `0` |
| `24000103` | `roguelike_tower_ui_card_select.ogg` | - | `0` | `2` |

### 奖励/领取/获得

共 19 条。优先检索关键词：`reward`, `claim`, `collect`, `congratulation`, `receive`, `item`, `coin`, `diamond`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `32` | `Sound_Receive_card_single.ogg` | SOUND_UI_RECEIVE_CARD: 弹出卡牌 | `0` | `0` |
| `36` | `Sound_UI_Win.wav` | BGSOUND_UI_COIN: 金钱背景音效 | `0` | `0` |
| `37` | `Increase_coin.ogg` | BGSOUND_UI_ITEM: 物品背景音效 | `0` | `0` |
| `53` | `UI_quest_reward_coin_collected.wav` | COIN_FLY | `0` | `2` |
| `54` | `ui_diamond_in_2.ogg` | DIAMOND_FLY | `0` | `2` |
| `55` | `UI_item.ogg` | ITEM_FLY | `0` | `0` |
| `59` | `Receive_card_single.ogg` | SOUND_UI_CARD_FLY: 卡牌飞出（所有箱子通用） | `0` | `0` |
| `63` | `Receive_cards_all.ogg` | SOUND_UI_AGAIN_DRAW_CARD_TEN_TIMES: 再次点击，十连抽的时候 | `0` | `0` |
| `15220005` | `C_collect.ogg` | CollectRss | `0` | `0` |
| `15220028` | `UI_claim.ogg` | Claim | `0` | `0` |
| `15220035` | `UI_item.ogg` | - | `0` | `0` |
| `15220079` | `UI_congratulation.wav` | UI_Congratulation: 转盘奖励弹窗音效 | `0` | `0` |
| `22200004` | `forest_treasure_reward.wav` | forest_treasure_reward: 点击龟壳破裂时音效 | `6` | `0` |
| `22200014` | `forest_treasure_collect_timespring.wav` | forest_treasure_collect_timespring: 时间泉水使用音效 | `6` | `0` |
| `22200015` | `forest_treasure_collect_sunstone.wav` | forest_treasure_collect_sunstone: 资源收集-太阳石音效 | `6` | `0` |
| `22200016` | `forest_treasure_collect_key.wav` | forest_treasure_collect_key: 资源收集-钥匙音效 | `6` | `0` |
| `22200017` | `forest_treasure_collect_crown.wav` | forest_treasure_collect_crown: 资源收集-皇冠音效 | `6` | `0` |
| `22200018` | `forest_treasure_collect_coin.wav` | forest_treasure_collect_coin: 资源收集-琥珀音效 | `6` | `0` |
| `26000005` | `Sound_Ui_Kingopoly_Claim_Wealth_Task.ogg` | - | `0` | `1` |

### 宝箱/卡牌/抽取

共 7 条。优先检索关键词：`chest`, `card`, `draw`, `box`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `60` | `Chest_wood_jump.ogg` | SOUND_UI_DRAW_CARD_JUMP_WOOD: 木箱：点击已开箱的箱子弹跳的动画 | `0` | `0` |
| `62` | `Chest_metal_jump.ogg` | SOUND_UI_DRAW_CARD_JUMP: 铁箱：点击已开箱的箱子弹跳的动画 | `0` | `0` |
| `22000036` | `collapse_card_in_place.wav` | - | `0` | `0` |
| `22000037` | `collapse_card_clear_up.wav` | - | `0` | `0` |
| `22000038` | `collapse_card_skill_shuffle.wav` | - | `0` | `0` |
| `22000039` | `collapse_card_skill_remove.wav` | - | `0` | `0` |
| `22000040` | `collapse_card_skill_recall.wav` | - | `0` | `0` |

### 升级/解锁/成长

共 21 条。优先检索关键词：`upgrade`, `levelup`, `lvup`, `unlock`, `star`, `skill_upgrade`, `waken`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `3` | `Sound_Scene_Unlock.wav` | SOUND_UI_UNLOCK: 解锁音效 | `0` | `0` |
| `9` | `Sound_Scene_LevelUp.wav` | - | `0` | `0` |
| `29` | `Sound_UI_Skill_Upgrade.ogg` | SOUND_UI_SKILL_UPGRADE: 技能升级 | `0` | `0` |
| `34` | `Sound_Scene_LevelUp.wav` | SOUND_UI_BAR_UPGRADE1: 进度条1 | `0` | `0` |
| `35` | `Sound_Scene_Success.wav` | SOUND_UI_BAR_UPGRADE2: 进度条2 | `0` | `0` |
| `15220002` | `C_c_levelup.wav` | - | `0` | `2` |
| `15220007` | `C_levelup.wav` | - | `0` | `0` |
| `15220016` | `Map_r_starts.ogg` | RallyStart | `3` | `0` |
| `15220068` | `Sound_UI_soldier_levelup.wav` | - | `0` | `0` |
| `15220069` | `Sound_UI_soldier_talent_levelup.wav` | - | `0` | `0` |
| `15220075` | `SFX_hero_levelup.wav` | HeroLvUpAndStarUp | `0` | `0` |
| `20000004` | `DragonStart.wav` | - | `6` | `0` |
| `21000001` | `Artifacts_Lvup.wav` | - | `0` | `0` |
| `22000022` | `halloween_slot_spin_start.ogg` | UI_ACTIVITY_SLOTMACHINE_SPIN_START: 老虎机转动开始 | `0` | `0` |
| `22200006` | `forest_treasure_merge_start.wav` | forest_treasure_merge_start: 合成预览音效 | `6` | `0` |
| `22200008` | `forest_treasure_levelup.wav` | forest_treasure_levelup: 工厂神庙升级音效 | `6` | `0` |
| `22200011` | `forest_treasure_cracker_start.wav` | forest_treasure_cracker_start: 爆炸预览音效 | `6` | `0` |
| `26000003` | `Sound_Ui_Kingopoly_Start_Effect.ogg` | - | `0` | `1` |
| `26000009` | `Sound_Ui_Kingopoly_Start_Effect_Speedup.ogg` | - | `0` | `1` |
| `190000003` | `ui_upgrade_effect_small.wav` | - | `0` | `0` |
| `190000004` | `ui_upgrade_effect_big.wav` | - | `0` | `0` |

### 错误/不可用/失败提示

共 9 条。优先检索关键词：`error`, `negative`, `buyerror`, `lost`, `defeat`, `lock`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `2` | `Sound_UI_Lost.wav` | SOUND_UI_LOST: 失败音效 | `1` | `0` |
| `17` | `Sound_Scene_Error.wav` | SOUND_SCENE_ERROR: 合成区满的音效 | `0` | `0` |
| `19` | `Sound_Scene_Comerror.wav` | - | `0` | `0` |
| `21` | `Sound_Scene_BuyError.wav` | SOUND_SCENE_BUYERROR: 金币不足购买 | `0` | `0` |
| `15220036` | `UI_negative.wav` | - | `0` | `0` |
| `15220053` | `Map_f_lose.wav` | FightDefeat | `3` | `0` |
| `22000034` | `capybara_game_lock_capybara.wav` | - | `0` | `0` |
| `24000105` | `Sound_UI_Lost.wav` | - | `1` | `0` |
| `25000008` | `Sound_Ui_LavaRush_Defeat.ogg` | - | `0` | `1` |

### 地图/行军/世界交互

共 33 条。优先检索关键词：`map`, `march`, `rally`, `teleport`, `shield`, `troop`, `world`, `unit`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `23` | `KG_March_FullMix_96bpm4-4(1).ogg` | SIMPLE_LEVEL_AUDIO: 普通关卡背景音乐 | `1` | `1` |
| `39` | `K1-WorldMap-loop.wav` | CITY_BUILDING_BG: 城建的背景音乐 | `2` | `3` |
| `57` | `amb_map.ogg` | WORLD_AMBIENT_BGM: 大世界环境背景音 | `3` | `1` |
| `15220006` | `C_h_troops.wav` | - | `0` | `0` |
| `15220012` | `Map_crd.ogg` | - | `3` | `0` |
| `15220014` | `Map_f_ongoing.ogg` | FightOngoing | `3` | `0` |
| `15220015` | `Map_r_creation.ogg` | LaunchRally | `3` | `0` |
| `15220017` | `Map_shieldon.ogg` | CityShieldOn | `3` | `0` |
| `15220018` | `Map_t_boost.wav` | - | `3` | `0` |
| `15220019` | `Map_t_charging.wav` | - | `3` | `1` |
| `15220020` | `Map_t_enter.wav` | - | `3` | `0` |
| `15220021` | `Map_teleport.ogg` | - | `3` | `0` |
| `15220039` | `UI_march.wav` | - | `0` | `0` |
| `15220040` | `KG_March_FullMix_96bpm4-4(1).wav` | - | `3` | `1` |
| `15220047` | `K1-WorldMap-War-loop.wav` | RallyAttack | `3` | `1` |
| `15220052` | `Map_f_won.wav` | FightVictory | `3` | `0` |
| `15220061` | `mus_map_V2_NO_PERCS_20210902.wav` | - | `3` | `1` |
| `15220072` | `mus_map_day.ogg` | WORLD_DAY_BGM: 大地图白天时背景音 | `3` | `1` |
| `15220073` | `mus_map_night.ogg` | WORLD_NIGHT_BGM: 大地图夜晚时背景音 | `3` | `1` |
| `15220074` | `SFX_castle_move.wav` | CityTeleport | `3` | `0` |
| `15220104` | `UI_toolbar_slide_world.ogg` | - | `0` | `0` |
| `15220110` | `map_building_valhalla.ogg` | Valhalla | `3` | `0` |
| `15220111` | `map_building_toolshed.ogg` | ToolsHome | `3` | `0` |
| `15220112` | `map_building_throne.ogg` | ThroneCity | `3` | `0` |
| `15220113` | `map_building_spring.ogg` | Water | `3` | `0` |
| `15220114` | `map_building_quarry.ogg` | Stone | `3` | `0` |
| `15220115` | `map_building_gold.ogg` | Mine | `3` | `0` |
| `15220116` | `map_building_dragonnest.ogg` | DragonHome | `3` | `0` |
| `15220117` | `map_building_castle.ogg` | PlayerCity | `3` | `0` |
| `24000001` | `mus_roguelike_tower_base.ogg` | - | `7` | `3` |
| `24000002` | `mus_roguelike_tower_grass.ogg` | - | `7` | `3` |
| `24000003` | `mus_roguelike_tower_lava.ogg` | - | `7` | `3` |
| `24000004` | `mus_roguelike_tower_snow.ogg` | - | `7` | `3` |

### 城市/建筑/生产

共 19 条。优先检索关键词：`city`, `building`, `castle`, `alliance`, `research`, `training`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `56` | `amb_city.ogg` | CITY_BUILDING_AMBIENT_BGM: 内城城建环境背景音 | `2` | `1` |
| `15220001` | `C_alliance.wav` | RequestAllianceHelp | `0` | `2` |
| `15220003` | `C_c_research.wav` | - | `0` | `2` |
| `15220004` | `C_c_training.wav` | - | `0` | `2` |
| `15220008` | `C_t_cavalry.wav` | - | `0` | `0` |
| `15220009` | `C_t_infantry.wav` | - | `0` | `0` |
| `15220010` | `C_t_range.wav` | - | `0` | `0` |
| `15220011` | `C_t_siege.wav` | - | `0` | `0` |
| `15220025` | `UI_alliance.wav` | - | `0` | `0` |
| `15220062` | `Sound_City_barracks.ogg` | - | `2` | `0` |
| `15220063` | `Sound_City_drunkery.ogg` | - | `2` | `0` |
| `15220064` | `Sound_City_gold.ogg` | - | `2` | `0` |
| `15220065` | `Sound_City_kingdomrecord.ogg` | - | `2` | `0` |
| `15220066` | `Sound_City_stone.ogg` | - | `2` | `0` |
| `15220100` | `UI_toolbar_slide_alliance.ogg` | - | `0` | `0` |
| `15220101` | `UI_toolbar_slide_castle.ogg` | - | `0` | `0` |
| `15220105` | `Sound_City_academy.ogg` | - | `2` | `0` |
| `15220106` | `Sound_City_castle.ogg` | - | `2` | `0` |
| `15220107` | `Sound_City_dragonden.ogg` | - | `2` | `0` |

### 战斗/技能/命中

共 312 条。优先检索关键词：`battle`, `fight`, `skill`, `attack`, `hit`, `launch`, `arrow`, `dragon`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `15010111` | `Sound_Battle_venom_launch_1.ogg` | - | `1` | `0` |
| `15010112` | `Sound_Battle_venom_launch_2.ogg` | - | `1` | `0` |
| `15010113` | `Sound_Battle_venom_launch_3.ogg` | - | `1` | `0` |
| `15010114` | `Sound_Battle_venom_launch_4.ogg` | - | `1` | `0` |
| `15010115` | `Sound_Battle_venom_launch_5.ogg` | - | `1` | `0` |
| `15010121` | `Sound_Battle_venom_hit_1.ogg` | - | `1` | `0` |
| `15010122` | `Sound_Battle_venom_hit_2.ogg` | - | `1` | `0` |
| `15010123` | `Sound_Battle_venom_hit_3.ogg` | - | `1` | `0` |
| `15010124` | `Sound_Battle_venom_hit_4.ogg` | - | `1` | `0` |
| `15010125` | `Sound_Battle_venom_hit_5.ogg` | - | `1` | `0` |
| `15010191` | `Sound_Battle_Venom_BB_1.wav` | - | `1` | `0` |
| `15010192` | `Sound_Battle_Venom_BB_2.wav` | - | `1` | `0` |
| `15010211` | `Sound_Battle_Shell_launch_1.ogg` | - | `1` | `0` |
| `15010212` | `Sound_Battle_Shell_launch_2.ogg` | - | `1` | `0` |
| `15010213` | `Sound_Battle_Shell_launch_3.ogg` | - | `1` | `0` |
| `15010214` | `Sound_Battle_Shell_launch_4.ogg` | - | `1` | `0` |
| `15010215` | `Sound_Battle_Shell_launch_5.ogg` | - | `1` | `0` |
| `15010221` | `Sound_Battle_Shell_hit_1.ogg` | - | `1` | `0` |
| `15010222` | `Sound_Battle_Shell_hit_2.ogg` | - | `1` | `0` |
| `15010223` | `Sound_Battle_Shell_hit_3.ogg` | - | `1` | `0` |
| `15010224` | `Sound_Battle_Shell_hit_4.ogg` | - | `1` | `0` |
| `15010225` | `Sound_Battle_Shell_hit_5.ogg` | - | `1` | `0` |
| `15010291` | `Sound_Battle_Shell_BB_1.wav` | - | `1` | `0` |
| `15010292` | `Sound_Battle_Shell_BB_2.wav` | - | `1` | `0` |
| `15010293` | `Sound_Battle_Shell_BB_3.wav` | - | `1` | `0` |
| `15010311` | `Sound_Battle_Ice_launch_1.ogg` | - | `1` | `0` |
| `15010312` | `Sound_Battle_Ice_launch_2.ogg` | - | `1` | `0` |
| `15010313` | `Sound_Battle_Ice_launch_3.ogg` | - | `1` | `0` |
| `15010314` | `Sound_Battle_Ice_launch_4.ogg` | - | `1` | `0` |
| `15010315` | `Sound_Battle_Ice_launch_5.ogg` | - | `1` | `0` |
| `15010321` | `Sound_Battle_Ice_hit_1.ogg` | - | `1` | `0` |
| `15010322` | `Sound_Battle_Ice_hit_2.ogg` | - | `1` | `0` |
| `15010323` | `Sound_Battle_Ice_hit_3.ogg` | - | `1` | `0` |
| `15010324` | `Sound_Battle_Ice_hit_4.ogg` | - | `1` | `0` |
| `15010325` | `Sound_Battle_Ice_hit_5.ogg` | - | `1` | `0` |
| `15010391` | `Sound_Battle_Ice_BB_1.wav` | - | `1` | `0` |
| `15010392` | `Sound_Battle_Ice_BB_2.wav` | - | `1` | `0` |
| `15010393` | `Sound_Battle_Ice_BB_3.wav` | - | `1` | `0` |
| `15010411` | `Sound_Battle_Arch_launch_1.ogg` | - | `1` | `0` |
| `15010412` | `Sound_Battle_Arch_launch_2.ogg` | - | `1` | `0` |

_还有 272 条同类配置，继续在 `AudioListCfg.tsv` 按关键词/ID 检索。_

### 活动玩法专用

共 27 条。优先检索关键词：`kingopoly`, `roguelike`, `treasure`, `slot`, `halloween`, `valentine`, `capybara`, `collapse`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `22000023` | `halloween_slot_spin_stop.ogg` | UI_ACTIVITY_SLOTMACHINE_SPIN_STOP: 老虎机停止 | `0` | `0` |
| `22000025` | `capybara_game_baby_capybara_remove.wav` | - | `0` | `0` |
| `22000026` | `capybara_game_baby_capybara_impact.wav` | - | `0` | `0` |
| `22000030` | `capybara_game_big_capybara_impact.wav` | - | `0` | `0` |
| `22000031` | `capybara_game_big_capybara_remove.wav` | - | `0` | `0` |
| `22000032` | `capybara_game_countdown_bomb.wav` | - | `0` | `0` |
| `22000033` | `capybara_game_capybara_boom.wav` | - | `0` | `0` |
| `22100003` | `kingdom_treasure_dig.ogg` | - | `0` | `0` |
| `22200001` | `music_forest_treasure.wav` | music_forest_treasure: 挖矿背景音乐 | `6` | `1` |
| `22200002` | `music_forest_treasure_begin.wav` | music_forest_treasure_begin: 挖矿预告背景音乐 | `6` | `1` |
| `22200003` | `forest_treasure_spin.wav` | forest_treasure_spin: 挖矿转盘音效 | `6` | `0` |
| `22200005` | `forest_treasure_merge_succeed.wav` | forest_treasure_merge_succeed: 合成结束音效 | `6` | `0` |
| `22200007` | `forest_treasure_merge_loop.wav` | forest_treasure_merge_loop: 合成循环音效 | `6` | `0` |
| `22200009` | `forest_treasure_fire.wav` | forest_treasure_fire: 发射音效 | `6` | `0` |
| `22200010` | `forest_treasure_dig.wav` | forest_treasure_dig: 挖掘音效 | `6` | `0` |
| `22200012` | `forest_treasure_cracker_loop.wav` | forest_treasure_cracker_loop: 爆炸循环音效 | `6` | `0` |
| `22200013` | `forest_treasure_cracker_explod.wav` | forest_treasure_cracker_explod: 爆炸音效 | `6` | `0` |
| `24000106` | `roguelike_tower_ui_slot_spin.ogg` | - | `1` | `0` |
| `24000107` | `roguelike_tower_ui_slot_get_hero.ogg` | - | `1` | `0` |
| `24000108` | `roguelike_effect_celebrating_vic.ogg` | - | `1` | `0` |
| `24001003` | `mus_valentine.ogg` | - | `0` | `0` |
| `26000001` | `Sound_Ui_Kingopoly_Roll_Dice.ogg` | - | `0` | `1` |
| `26000002` | `Sound_Ui_Kingopoly_Square_Light.ogg` | - | `0` | `1` |
| `26000004` | `Sound_Ui_Kingopoly_King_Run.ogg` | - | `0` | `1` |
| `26000007` | `Sound_Ui_Kingopoly_Trigger_Event_Turn.ogg` | - | `0` | `1` |
| `26000008` | `Sound_Ui_Kingopoly_Roll_Dice_Speedup.ogg` | - | `0` | `1` |
| `26000010` | `Sound_Ui_Kingopoly_King_Run_Speedup.ogg` | - | `0` | `1` |

### BGM/环境/循环

共 9 条。优先检索关键词：`music`, `mus_`, `bgm`, `amb`, `loop`, `soundtrack`

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `25` | `mus_splash_NO_CHOIR.ogg` | LOADING_BG: loading时的背景音乐 | `4` | `1` |
| `15220041` | `CivilizedAmbiance_4.ogg` | - | `0` | `1` |
| `15220042` | `ApesTavernIntro.wav` | - | `0` | `0` |
| `15220043` | `ApesTavernLoop.wav` | - | `0` | `0` |
| `15220044` | `FTEIntroMusic.wav` | - | `0` | `0` |
| `15220045` | `FTESFXmusic.wav` | - | `0` | `0` |
| `15220055` | `ConvoySpeedUp.wav` | - | `3` | `0` |
| `21000002` | `Artifacts_Loop.wav` | - | `0` | `0` |
| `27000001` | `mus_childrens_day.ogg` | ChildrensDay_BGM | `0` | `3` |

### 其他/待人工试听

共 204 条。优先检索关键词：``

| ID | 资源/文件名 | 备注/常量 | 场景 | 类型 |
|---|---|---|---|---|
| `1` | `Sound_UI_Win.wav` | SOUND_UI_WIN: 胜利音效 | `1` | `0` |
| `4` | `Sound_Scene_Success.wav` | SOUND_SCENE_SUCCESS: 士兵合成成功音效 | `1` | `0` |
| `5` | `Sound_Scene_Shelve_1.wav` | SOUND_SCENE_SHELVE_1: 放置士兵的音效 | `1` | `0` |
| `6` | `Sound_Scene_Place.ogg` | - | `1` | `0` |
| `8` | `Sound_Scene_Mention.wav` | SOUND_SCENE_MENTION: 点击提起士兵的音效 | `0` | `0` |
| `10` | `Sound_Scene_Gold_Get_1.wav` | - | `0` | `0` |
| `11` | `Sound_Scene_Gold_Get_2.wav` | - | `0` | `0` |
| `12` | `Sound_Scene_Gold_Get_3.wav` | - | `0` | `0` |
| `13` | `Sound_Scene_Gold_Drop_1.wav` | - | `0` | `0` |
| `14` | `Sound_Scene_Gold_Drop_2.wav` | - | `0` | `0` |
| `15` | `Sound_Scene_Gold_Drop_3.wav` | - | `0` | `0` |
| `16` | `Sound_Scene_Gold_Drop_4.wav` | - | `0` | `0` |
| `18` | `Sound_Scene_Destroy.ogg` | SOUND_SCENE_DESTORY: 销毁士兵 | `0` | `0` |
| `22` | `Sound_Scene_Buy.wav` | SOUND_SCENE_BUY: 点击造兵按钮 | `0` | `0` |
| `24` | `KG_Boss_FullMix_104bpm4-4(1).ogg` | BOSS_LEVEL_AUDIO: boss关卡背景音乐 | `1` | `1` |
| `38` | `Increase_exp.ogg` | BGSOUND_UI_HERO: 英雄背景音效 | `0` | `0` |
| `40` | `K1-Voiceover-1.1.wav` | - | `1` | `1` |
| `41` | `K1-Voiceover-2.1.wav` | - | `1` | `1` |
| `42` | `K1-Voiceover-3.1.wav` | - | `1` | `1` |
| `43` | `K1-Voiceover-4.1.wav` | - | `1` | `1` |
| `44` | `K1-Voiceover-5.1.wav` | - | `1` | `1` |
| `45` | `K1-Voiceover-6.1.wav` | - | `1` | `1` |
| `46` | `K1-Voiceover-7.1.wav` | - | `1` | `1` |
| `47` | `K1-Voiceover-8.1.wav` | - | `1` | `1` |
| `48` | `K1-Voiceover-9.1.wav` | - | `1` | `1` |
| `49` | `K1-Voiceover-10.1.wav` | - | `1` | `1` |
| `50` | `K1-Voiceover-11.1.wav` | - | `1` | `1` |
| `51` | `K1-Voiceover-12.1.wav` | - | `1` | `1` |
| `52` | `K1-Voiceover-13.1.wav` | - | `3` | `1` |
| `15010501` | `zombie_venom_01.wav` | - | `1` | `0` |
| `15010502` | `zombie_explosion_01.wav` | - | `1` | `0` |
| `15010503` | `zombie_chain_01.wav` | - | `1` | `0` |
| `15220023` | `S_sendmessage.ogg` | - | `0` | `0` |
| `15220024` | `UI_achievement.wav` | - | `0` | `0` |
| `15220037` | `UI_prompt.ogg` | - | `0` | `0` |
| `15220054` | `S_breaking.wav` | - | `3` | `0` |
| `15220067` | `Sound_UI_point_get.wav` | - | `0` | `0` |
| `15220078` | `UI_spinwheel.ogg` | UI_Spinwheel: 转盘旋转音效 | `0` | `0` |
| `15220091` | `UI_menu_slide_calendar.ogg` | - | `0` | `0` |
| `15220092` | `UI_menu_slide_event.ogg` | - | `0` | `0` |

_还有 164 条同类配置，继续在 `AudioListCfg.tsv` 按关键词/ID 检索。_

## 快速检索命令

```powershell
rg -n -i "click|button|close|reward|claim|chest|upgrade|unlock|error|map|march|skill|loop" k1_client\client\Assets\Res\config\AudioListCfg.tsv
rg --files k1_client\client\Assets\k1\K1D1\Res\Audios k1_client\client\Assets\k1\Res\Audio k1_client\client\Assets\Res\Audio | rg -i "click|button|close|reward|claim|chest|upgrade|unlock|error|map|march|skill|loop"
```

## 维护

K1 音频资源或配表变化后，在 K1 仓库根目录运行：

```powershell
python scripts/build_k1_audio_library.py --project-root <K1仓库根> --output references/k1-audio-library.md --json-output references/k1-audio-library.json
```
