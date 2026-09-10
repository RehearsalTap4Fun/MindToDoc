# Naming And Reuse Rules

## Core Model

- `事件名`：程序触发点，对应 `AudioEvent.事件名`。
- `音效资源名`：真实音频资源或文件名，不含扩展名。
- 两者是多对一关系：多个事件可以复用同一个资源。

如果多个事件共享同一个声音，必须使用完全相同的 `音效资源名`。

示例：

| 事件名 | 音效资源名 |
|---|---|
| `ui_rogue_choice_refresh_free` | `ui_rogue_choice_refresh_free` |
| `ui_rogue_choice_refresh_pay` | `ui_rogue_choice_refresh_free` |
| `ui_rogue_slotmachine_refresh` | `ui_rogue_choice_refresh_free` |

不要为了同一个声音发明别名，例如 `ui_rogue_choice_refresh_shuffle`，除非它确实是另一份独立音频文件。

## Event Names

- 使用 lowercase snake case。
- 不带 `Play_` 或 `Stop_` 前缀。
- UI 音效以 `ui_` 开头。
- 循环事件建议用 `_loop` 后缀。
- 停止循环时，程序对同一个事件名调用 `StopEvent`。

## Asset Names

- 通用 UI 资源：`common_<action>`。
- 功能专属 UI 资源：`ui_<feature>_<action>`。
- 角色或世界音效：`<dev_name>_<action>`。

常用通用资源名：

- `common_btn_click`
- `common_btn_close`
- `common_popup_open`
- `common_popup_close`
- `common_tab_switch`
- `common_item_select`
- `common_locked_click`
- `common_reward_get`

## Split Scope

只拆玩家能听到的触发：

- UI 打开/关闭。
- 按钮点击、确认、取消。
- 卡牌/道具选择。
- 奖励获得。
- 稀有度揭示。
- 刷新/重随成功。
- 资源不足反馈。
- 动画或 VFX 同步音。
- 滚动、蓄力、环境、发光等循环。
- 3D/world 的释放、命中、弹道、冲击、出生、死亡。

不要把纯配置字段、概率规则、文本 key、消耗 ID、后端状态或算法描述拆成音效需求，除非它们直接导致玩家听到反馈。

## Tag Decisions

- `新增`: 需要一份新音频资源。必须有声音设计说明、公司库检索方向或 AI prompt。
- `复用`: 只能指向当前工作区已经存在且可播放的 `audio/<asset>.ogg`。声音足够通用但文件不存在时,也必须标 `新增` 先生产成真实资源。
- `沿用X1`: 只有完成导出、转码、命名映射,并且当前工作区已有可播放的 `audio/<asset>.ogg` 后才能使用。不要把未迁移的 X1 名称当作复用。

`复用` / `沿用X1` 行仍然属于真实事件,必须进入最终交付清单或配置意图表。判断复用时,先查真实文件是否存在,再看声音显著性和主题专属性。不能只因为资源名是 `common_xxx` 或历史上“应该有”,就标为复用。

如果同一个 `音效资源名` 在本轮首次制作,所有引用该 asset 的事件都仍应标 `新增`;资产层面只制作一次。只有这份资源已经转成 `audio/<asset>.ogg` 并通过交付校验后,后续需求才允许标 `复用`。

## X15 Tone

项目默认声音方向：

- 原始奇幻。
- 轻半卡通。
- 神秘但可读。
- 古老神圣秩序被扭曲。
- 雾、誓约、仪式、觉醒、束缚能量可作为色彩。
- 移动商业化可读性优先。

避免：

- 科幻。
- 生物工程。
- 协议/权限/系统控制语汇。
- 热带 troll/Loa/羽骨图腾感。
- 重度邪教恐怖或血腥。
- 泛中世纪王国感。

## K1 项目复用

K1 不使用 X15 的 `common_xxx` 通用池命名；复用判断以 **K1 AudioList 实际资源** 为准。

### 查库顺序

1. `references/k1-audio-library.md` — 人工可读，含常用复用入口与分类索引。
2. `references/k1-audio-library.json` — 精确检索 ID、文件名、`const_name`、备注。
3. `scripts/build_k1_audio_library.py` — 从 K1 仓库 `AudioListCfg.tsv` + 音频文件名刷新上述两份索引。

### K1 复用标注

| 标注 | `asset` 填什么 | 说明 |
|------|----------------|------|
| `复用` | AudioList ID（如 `15220034`）或已有文件名（如 `UI_i_generic.ogg`） | 必须在 k1-audio-library 中命中同类语义 |
| `新增` | 新资源名 | 必须写 `desc` + `prompt` + `library_queries` |
| `沿用X1` | X1 资源名 | K1 库无对应项、需从 X1 迁移时；须注明需 X1 库复核 |

### K1 优先复用语义

| 触发/语义 | 优先查库关键词 |
|-----------|----------------|
| 通用按钮点击 | `UIGeneric`、`UI_i_generic`、`button`、`click`、`generic` |
| 关闭/返回 | `UI_close`、`UI_back`、`close`、`back`、`Menu_close` |
| 弹窗/界面开关 | `popup`、`open`、`close`、`window`、`Menu_open` |
| 页签/选中/切换 | `switch`、`select`、`label`、`horizontal` |
| 奖励领取/获得 | `claim`、`reward`、`collect`、`receive`、`congratulation` |
| 宝箱/卡牌 | `chest`、`card`、`draw`、`box` |
| 升级/解锁/成功 | `upgrade`、`levelup`、`unlock`、`success`、`star` |
| 错误/不可点击 | `error`、`negative`、`buyerror`、`lock` |
| 地图/行军/传送 | `map`、`march`、`teleport`、`troop`、`rally`、`shield` |
| BGM/环境/循环 | `music`、`mus_`、`bgm`、`amb`、`loop` |

K1 拆需求时，`bank` / `module` 按 K1 模块习惯填写；进入 X15 正式生产流水线前，需将资源名与 X15 命名规则对齐。
