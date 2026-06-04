# 2026世界杯主题活动 · 音效需求表

**整理日期**：2026-06-02  
**修订**：足球精简；积分赛/淘汰赛/商业化/可选-P2 改为复用，不单独量产  
**来源文档**：`output/2026世界杯主题活动-开发文档.md`  
**适用范围**：移动端 iOS / Android，竖屏单手操作，主游戏内限时活动  
**生成方式**：计划使用 AI 文生音频；下表「Text-to-Audio Prompt」为完整可复制提示词（英文）

---

## 1. 使用说明

### 1.1 类型字段

| 类型 | 说明 |
|------|------|
| BGM | 背景音乐循环/段落 |
| 通用UI | 按钮、选中、弹窗、开关、错误等，全活动复用 |
| 通用-奖励 | 获得奖励、领奖、任务完成等正向反馈（**全活动一条**） |
| 足球 | 切片局内、守门、道具、关卡结算、创角生涯 |
| 竞猜 | 下注、锁定、结算、竞猜币；独立保留 |
| 养成 | 升级、合同、成就等养成专属（无特色则复用通用-奖励 / 通用UI） |

> **积分赛、淘汰赛、商业化、可选-P2 不再单独占行**，见 §1.2 复用表。

### 1.2 合并与复用规则

**通用 UI（9 条）** — 不变。

**通用-奖励（1 条）**

| 保留 ID | 复用场景（不再单独做音效） |
|---------|---------------------------|
| `SFX_REWARD_POP` | 关卡结算奖励条、赛季目标发奖、排名/BP/礼包/商店领取、每日任务完成、淘汰赛名次奖等**凡「到账/弹出奖励」** |

**足球（15 条）** — 见 §1.2 历史合并表（切片成败、踢球、道具等）。

| 合并为 | 吸收的原 ID |
|--------|-------------|
| `SFX_SLICE_FAIL` | 多种切片/守门失败 |
| `SFX_SLICE_SUCCESS` | 进球 + 庆祝 |
| `SFX_KICK` | 射门 + 传球 |
| `SFX_GK_DIVE` | 左/右扑 |
| `SFX_MATCH_OTHER` | 关卡平/负 |
| — | `CONTRACT_SIGN`→`UI_CLICK`；试训弹窗→`UI_POPUP_OPEN` |

**竞猜（6 条）** — 不变。

**养成（5 条 → 3 条）**

| 保留 | 复用 |
|------|------|
| `SFX_LEVEL_UP` | 原 `FAME_LEVEL_UP` + `LIFE_LEVEL_UP` + **`BP_LEVEL_UP`（商业化）** |
| `SFX_COIN_SPEND` | 花金币升级生活 |
| `SFX_CONTRACT_NEW` | 联赛轮新合同（有「拆信封」语义，保留） |
| `SFX_ACHIEVEMENT_UNLOCK` | 成就达成 |
| — | 若成就与升级听感可统一，可再并到 `SFX_LEVEL_UP`（当前仍保留成就一条） |

**积分赛（0 条 · 全部复用）**

| 场景 | 复用音效 |
|------|----------|
| 小关解锁 | `SFX_UI_SELECT` |
| 一轮联赛大关完成 | `SFX_MATCH_WIN`（里程碑庆祝） |
| 赛季绝对目标达成发奖 | `SFX_REWARD_POP` |

**淘汰赛（0 条 · 全部复用）**

| 场景 | 复用音效 |
|------|----------|
| 创建/加入/同意入队 | `SFX_UI_CLICK` |
| 入队拒绝 | `SFX_UI_NEGATIVE` |
| 阶段开赛弹窗（CHAMPIONSHIP GAME） | `SFX_UI_POPUP_OPEN` |
| 海选/单淘汰**晋级** | `SFX_MATCH_WIN` |
| 淘汰/未晋级 | `SFX_MATCH_OTHER` |
| 淘汰赛界面氛围 | `BGM_04`（可选，P2） |

**商业化（0 条专用 · 仅复用）**

| 场景 | 复用音效 |
|------|----------|
| 奖励条弹出 / BP领奖 / 商店买到 / 礼包 / 每日任务 | `SFX_REWARD_POP` |
| 商店/礼包**购买确认** | `SFX_UI_CLICK` |
| BP 等级提升 | `SFX_LEVEL_UP` |
| 排名/淘汰赛**大额领奖**（若 UI 为开箱庆祝） | `SFX_REWARD_POP`（多条连播）或 `SFX_MATCH_WIN`（仅当需要强庆祝时） |

**可选-P2（0 条 · 不制作）**

| 原需求 | 处理 |
|--------|------|
| 角球 / 界外球 | 直接用 `SFX_KICK` |
| 球场观众 bed | 不做；依赖 `BGM_02` |
| 花式射门等 | 不做 |

### 1.3 通用 Negative Prompt（SFX）

```text
music, melody, song, voice, speech, crowd chant loop, long reverb tail, cinematic trailer, distorted, clipping, noisy, muddy mix
```

### 1.4 批量生成与导出

- 每条生成 3–5 变体：`{ID}_v01.ogg`。
- 裁切至「建议时长」；SFX 峰值约 -1 dBTP。
- 双端：Android `.ogg`，iOS AAC/CAF。

---

## 2. 音效需求总表

> 下表**仅列需要单独制作的 ID**；积分赛 / 淘汰赛 / 商业化 / 可选-P2 见 §1.2。

| ID | 类型 | 优先级 | 建议时长 | 中文用途描述 | Text-to-Audio Prompt（完整版） |
|----|------|--------|----------|--------------|--------------------------------|
| BGM_01 | BGM | P1 | 60–90s 循环 | 活动主界面、球星养成页背景音乐 | Upbeat modern sports menu music, light electronic drums, subtle stadium ambience, FIFA world cup mood, positive, medium tempo, seamless loopable, no vocals, clean mobile game mix |
| BGM_02 | BGM | P0 | 45–60s 循环 | 切片操作局内底噪 | Tense but playful mobile soccer mini-game background loop, soft percussion, low strings pulse, minimal melody, non-intrusive, seamless loopable, no vocals, clean mix |
| BGM_03 | BGM | P1 | 15–30s | 创角开场视频 | Dramatic soccer free kick moment underscore, rising tension, ends with single kick impact, cinematic sports, no commentary, no vocals, clean mix |
| BGM_04 | BGM | P2 | 45s 循环 | 淘汰赛对阵树、竞猜大厅（可选） | Competitive esports tournament lobby music, driving rhythm, subtle horn stabs, exciting but clean, loopable, no vocals |
| SFX_UI_CLICK | 通用UI | P0 | 0.15–0.25s | 普通按钮：确认、返回、关闭、进关卡、页签、回放、合同签约、**商店/礼包购买确认**、组队操作等 | Generic mobile game UI button tap click, soft plastic button, neutral positive feedback, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_UI_SELECT | 通用UI | P0 | 0.15s | 选中态：选角、国籍、球队卡、列表高亮、**积分赛小关解锁**、竞猜选项选中 | UI selection highlight blip, light tick pitch up, character picker feedback, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_UI_POPUP_OPEN | 通用UI | P0 | 0.25s | 弹窗出现：试训完成、合同、回溯、下注/结算、**淘汰赛阶段开赛**等 | Modal popup window appear, soft whoosh upward, mobile game UI, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_UI_POPUP_CLOSE | 通用UI | P0 | 0.2s | 弹窗关闭 | Modal popup window close, soft whoosh downward, mobile game UI, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_UI_TOGGLE_ON | 通用UI | P0 | 0.2s | 瞄准辅助线等开关打开 | UI toggle switch on, high pitch blip, targeting enabled, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_UI_TOGGLE_OFF | 通用UI | P0 | 0.2s | 瞄准辅助线等开关关闭 | UI toggle switch off, low pitch blip, targeting disabled, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_UI_NEGATIVE | 通用UI | P0 | 0.3s | 不可操作：资源不足、下注截止、置灰点击、**入队拒绝** | Soft error buzz, action denied, insufficient resources, mobile game UI, not harsh alarm, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_UI_PAUSE_OPEN | 通用UI | P0 | 0.25s | 局内暂停打开 | Game pause menu open, soft pop, game paused state, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_UI_PAUSE_CLOSE | 通用UI | P0 | 0.25s | 关闭暂停 | Game resume, pause menu close, soft pop, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_REWARD_POP | 通用-奖励 | P0 | 0.3s | **全活动奖励到账/弹出**：关卡结算每条奖励、赛季目标、BP领奖、礼包、每日任务、排名发放等 | Coin reward pop, bright chime sparkle, loot item appear, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_SLICE_ENTER | 足球 | P0 | 0.3s | 进入切片 | Soft whoosh transition into soccer kickoff moment, subtle referee whistle hint in distance, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_MODE_LOCK | 足球 | P0 | 0.3s | 本关操作模式锁定确认 | Mode locked confirm thunk, firm mechanical latch click with short positive tail, decisive UI commit, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_BALL_RELEASE | 足球 | P0 | 0.3s | 弹弓松手射出 | Snappy rubber band release pop with light whoosh, cartoon elastic snap, soccer mini game, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_KICK | 足球 | P0 | 0.4s | 射门、传球、角球/界外球（P2 不单独做） | Soccer ball kick impact on grass, crisp thump, outdoor stadium foley, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_SLICE_SUCCESS | 足球 | P0 | 1.0s | 切片成功统一音 | Soccer ball hits goal net rustle swish plus short victory sting, brief crowd cheer burst, satisfying mobile soccer success, no vocals, no full music bed, clean mix |
| SFX_SLICE_FAIL | 足球 | P0 | 0.8s | 切片/守门失败统一音；细分类靠 UI | Short sports slice fail feedback, gentle descending tone, hint of blocked save or missed attempt, not harsh buzzer, mobile game, no vocals, no full music bed, clean mix |
| SFX_GK_TICK | 足球 | P0 | 0.08s | 守门倒计时滴答 | Digital clock timer tick beep, clean UI countdown, clean mobile game sfx, very short, no vocals, no music bed, single hit, dry mix |
| SFX_GK_SAVE_SUCCESS | 足球 | P0 | 0.5s | 守门切片成功 | Successful goalkeeper catch, gloves gripping ball, positive confirm chime, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_GK_DIVE | 足球 | P0 | 0.5s | 守门飞身（左/右 pan） | Goalkeeper dive body launch, glove ball touch and grass landing thud, athletic save foley, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_ITEM_WHISTLE | 足球 | P0 | 0.5s | 哨子道具 | Referee whistle sharp two-tone blast, extra play granted, authoritative sports, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_ITEM_REWIND | 足球 | P0 | 0.8s | 回溯确认 | Tape rewind glitch whoosh, time reverse swoosh, short VHS rewind, ends with soft click reset, clean mobile game sfx, no vocals, no music bed, dry mix |
| SFX_MATCH_WIN | 足球 | P0 | 1.5s | 关卡结算胜；**联赛轮完成、淘汰赛晋级** | Short match win fanfare, triumphant horns, soccer victory result, mobile game, no vocals, clean mix |
| SFX_MATCH_OTHER | 足球 | P0 | 1.0s | 关卡平/负；**淘汰赛淘汰** | Neutral match end tone, mild low brass or whistle, non-win result, restrained not depressing, no vocals, clean mix |
| SFX_TRAINING_DONE | 足球 | P0 | 0.5s | 试训完成轻庆祝（可选，可仅 POPUP） | Training step complete soft chime, short positive ping, mobile sports tutorial, clean mobile game sfx, no vocals, no music bed, single hit, dry mix |
| SFX_SIGNING_FANFARE | 足球 | P1 | 1.8s | 签约亮相过场 | Player unveiling short fanfare, camera flash pops, soccer star debut ceremony, no vocals, clean mix |
| SFX_BET_PLACE | 竞猜 | P1 | 0.3s | 确认下注 | Sports betting chip place confirm click, casino chip on table, crisp, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_BET_CHANGE | 竞猜 | P1 | 0.25s | 修改已下注 | Bet slip update, paper shuffle UI, sports wagering interface, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_BET_LOCK | 竞猜 | P1 | 0.35s | 下注截止锁定 | Betting window closed, lock click deadline, firm UI feedback, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_BET_WIN | 竞猜 | P1 | 1.0s | 结算命中 | Bet win coins shower, bright positive jackpot micro stinger, sports betting success, no vocals, clean mix |
| SFX_BET_LOSE | 竞猜 | P1 | 0.8s | 结算未中 | Bet lose soft negative feedback, coins taken away, restrained disappointment, no harsh alarm, no vocals, clean mix |
| SFX_BET_COIN_GET | 竞猜 | P1 | 0.4s | 竞猜币到账 | Betting coins received, stack clink, currency add, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_LEVEL_UP | 养成 | P1 | 0.8s | 知名度/生活/**BP** 等级提升统一 | Level up sparkle chime, RPG upgrade bright, mobile game progression, clean mobile game sfx, no vocals, clean mix |
| SFX_COIN_SPEND | 养成 | P1 | 0.3s | 花费金币升级生活 | Coins spent clinking descending, light cash register, clean mobile game sfx, short, no vocals, no music bed, single hit, dry mix |
| SFX_CONTRACT_NEW | 养成 | P1 | 0.6s | 联赛轮结束发放新合同 | New contract envelope open, official stamp, sports agent deal sealed, clean mobile game sfx, no vocals, clean mix |
| SFX_ACHIEVEMENT_UNLOCK | 养成 | P1 | 0.8s | 成就达成 | Achievement trophy unlock micro fanfare, badge ping, clean mobile game sfx, no vocals, clean mix |

---

## 3. 程序映射速查

```text
// 通用 UI
PlayUiClick()        -> SFX_UI_CLICK
PlayUiSelect()       -> SFX_UI_SELECT      // 含积分赛小关解锁
PlayUiPopup(open)    -> open ? SFX_UI_POPUP_OPEN : SFX_UI_POPUP_CLOSE
PlayUiToggle(on)     -> on ? SFX_UI_TOGGLE_ON : SFX_UI_TOGGLE_OFF
PlayUiNegative()     -> SFX_UI_NEGATIVE    // 含入队拒绝
PlayUiPause(open)    -> open ? SFX_UI_PAUSE_OPEN : SFX_UI_PAUSE_CLOSE

// 通用-奖励（积分赛发奖 / 商业化领奖 / 任务完成等）
OnRewardPop()        -> SFX_REWARD_POP

// 足球
OnSliceEnter()       -> SFX_SLICE_ENTER
OnModeLock()         -> SFX_MODE_LOCK
OnBallRelease()      -> SFX_BALL_RELEASE
OnKick()             -> SFX_KICK           // 含角球/界外球
OnSliceSuccess()     -> SFX_SLICE_SUCCESS
OnSliceFail()        -> SFX_SLICE_FAIL
OnGkTick()           -> SFX_GK_TICK
OnGkSaveSuccess()    -> SFX_GK_SAVE_SUCCESS
OnGkDive(pan)        -> SFX_GK_DIVE
OnItemWhistle()      -> SFX_ITEM_WHISTLE
OnItemRewind()       -> SFX_ITEM_REWIND
OnMatchResult(win, draw, lose)
  win                -> SFX_MATCH_WIN      // 含联赛轮完成、淘汰赛晋级
  draw|lose          -> SFX_MATCH_OTHER  // 含淘汰赛淘汰

// 养成
OnLevelUp()          -> SFX_LEVEL_UP       // 含 BP 升级
OnCoinSpend()        -> SFX_COIN_SPEND
OnContractNew()      -> SFX_CONTRACT_NEW
OnAchievement()      -> SFX_ACHIEVEMENT_UNLOCK

// 积分赛 / 淘汰赛 / 商业化：无专用接口，见 §1.2

// 竞猜
PlayBetPlace()       -> SFX_BET_PLACE
PlayBetSettle(win)   -> win ? SFX_BET_WIN : SFX_BET_LOSE
OnBetCoinGet()       -> SFX_BET_COIN_GET
```

---

## 4. 验收要点

| 检查项 | 标准 |
|--------|------|
| 需量产条数 | 以 §2 总表为准，**不含**已删除的积分赛/淘汰赛/商业化/P2 行 |
| 奖励类 | 到账/弹出统一 `REWARD_POP`，不与 `UI_CLICK` 混用场景 |
| 淘汰赛晋级/淘汰 | 复用 `MATCH_WIN` / `MATCH_OTHER`，不单独做 tournament 音效 |
| 竞猜 | 仍用 `SFX_BET_*` |
| 足球成败 | `SLICE_SUCCESS` / `SLICE_FAIL` 可区分 |

---

## 5. 数量统计

| 类型 | 需制作条数 | 说明 |
|------|------------|------|
| BGM | 4 | `BGM_04` 可选 P2 |
| 通用UI | 9 | |
| 通用-奖励 | 1 | 替代原商业化 7 条 |
| 足球 | 15 | |
| 竞猜 | 6 | |
| 养成 | 4 | 原 5→4（等级合并） |
| 积分赛 | **0** | 复用 UI / MATCH / REWARD |
| 淘汰赛 | **0** | 复用 UI / MATCH / BGM_04 |
| 商业化 | **0** | 复用 REWARD / CLICK / LEVEL_UP |
| 可选-P2 | **0** | 不制作 |
| **合计** | **39** | 原 59 |

---

## 6. 关联文档

- 开发文档：`output/2026世界杯主题活动-开发文档.md`
- 美术需求：`docs/art/2026-worldcup-activity-art-requirements.md`
