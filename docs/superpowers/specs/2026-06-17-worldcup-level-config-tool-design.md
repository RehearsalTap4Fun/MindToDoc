# 2026 世界杯活动 · 关卡 Tag 配置工具 设计文档

**日期**: 2026-06-17
**状态**: 已实现,待接入主配置合并流程
**模板依据**: `templates/config-tool-spec.md`

---

## 1. 定位

- **工具职责**:策划在 `LevelTagCfg.xlsx` 中按关贴语义 tag → 工具读 tag 在现有 tier 默认基础上做 patch → 输出关卡相关 8 张配置表的独立 xlsx。
- **使用者**:数值/关卡策划。
- **触发方式**:命令行,`python3 output/test-config/level-tags/apply_level_tags.py`(单条命令一份产物)。
- **不做的事**:
  - 不替换现有 `generate_activity_soccer_test_config.py`(主生成器仍是关卡以外所有表的真源)。
  - 不生成专属切片实例(只引用现有 120 库实例)。
  - 不支持 tag 带参数、不支持跨关粒度。

---

## 2. 输入形态

| 维度 | 决定 |
|---|---|
| 输入语义 | 关卡风格标签(语义词,如 `pressure` / `boss` / `set_piece`) |
| 与默认体系关系 | **tier 默认 + tag 调整**:基线复用 `generate_activity_soccer_test_config.py` 的 `_tier_specs / _compose_slice_list / _build_levels` 逻辑,tag 对单关行做 patch |
| 输入文件格式 | xlsx(`LevelTagCfg.xlsx`) |
| 输入路径 | `output/test-config/level-tags/LevelTagCfg.xlsx` |
| 是否必须 | **必须提供**,文件缺失则报错退出 |

### 2.1 LevelTagCfg.xlsx 结构

文件含两个页签:

**页签 1 `LevelTags`**(策划填表入口,500 行):

| 列 | 类型 | 说明 |
|---|---|---|
| ID | int | level_id,1..500,与 `ActvSoccerLevelCfg.ID` 对齐 |
| Round | int | 所属轮次 1..50,= `ceil(ID/10)`,只读校验 |
| LevelInRound | int | 轮内序号 1..10,= `((ID-1) % 10)+1`,只读校验 |
| Tier | int | 1..10,= `ceil(Round/5)`,只读校验 |
| Tags | string | 该关贴的 tag 列表,英文逗号或空格分隔;空 = 仅走 tier 默认 |
| Note | string | 策划备注,工具不读 |

**页签 2 `TagDef`**(词表对照与互斥校验):

| 列 | 类型 | 说明 |
|---|---|---|
| Tag | string | tag 名(小写蛇形) |
| Affects | string | 受影响字段类(`slice` / `ai` / `level`),逗号分隔 |
| Description | string | 中文释义,人读 |
| MutexGroup | string | 互斥组名,留空表示不与其他冲突 |

> `TagDef` 页**只用于人读对照与冲突校验**;每个 tag 的 patch 实际逻辑写在 `level_tag_lib.py`,工具加载时核对两侧 tag 名一致(`TagDef.Tag` 集合 ⊆ lib 注册表),不一致则报错。

---

## 3. 词表

### 3.1 起点

由 AI 提初版 12-16 个 tag,据 `generate_activity_soccer_test_config.py` 现有默认逻辑提取候选,覆盖切片组成 / AI·难度·Modifier / 对手·阈值·门票三类。初版词表如下:

| Tag | Affects | 互斥组 | 释义 |
|---|---|---|---|
| `tutorial` | slice, level | tutorial | 强制 IsTutorial=1,SliceList=[201,202,203],TicketCost=0 |
| `set_piece` | slice | — | 强制至少 1 个 free_kick + 1 个 penalty 切片(顺序保留) |
| `corner_focus` | slice | — | 末位强制 corner v2 |
| `gk_test` | slice | — | 末位强制 goalkeep v2(守门考验) |
| `long_match` | slice | length | 切片数 +1(上限 5) |
| `short_match` | slice | length | 切片数 -1(下限 2) |
| `all_v2` | slice | — | SliceList 内全部切片用 v2 复合变体 |
| `hard_plus` | ai | difficulty | AiProfileID +1(上限 1010),OpponentTeamStar +1(上限 5) |
| `easy_minus` | ai | difficulty | AiProfileID -1(下限 1001),OpponentTeamStar -1(下限 1) |
| `extreme_keeper` | ai | modifier | SliceAi.ModifierID 强制 4005(极限移动门将,仅作用于该关 SliceAi 行) |
| `no_modifier` | ai | modifier | SliceAi.ModifierID 强制 0 |
| `narrow_angle` | ai | modifier | SliceAi.ModifierID 强制 4006(收窄夹角) |
| `boss` | level | — | OpponentTeamStar=5,WinThreshold=切片数(全胜) |
| `must_win` | level | threshold | WinThreshold = 切片数,DrawThreshold = WinThreshold-1(无平局) |
| `lenient` | level | threshold | WinThreshold = max(1, ceil(n*0.4)),DrawThreshold = max(1, win-1) |
| `free_run` | level | — | TicketCost=0(不消耗门票) |

### 3.2 参数化

**纯枚举**,tag 是固定串。表中如出现未注册 tag,工具报错退出。

### 3.3 词表定义位置

- **业务真相**:`level_tag_lib.py` 中每个 tag 对应一个 `patch(level_row, slice_ai_rows, level_in_round, tier) -> None` 函数,统一注册到 `TAG_REGISTRY: dict[str, TagSpec]`。
- **人读对照 + 互斥校验**:`LevelTagCfg.xlsx` 内 `TagDef` 页签;运行时校验 `TagDef.Tag` 与 `TAG_REGISTRY.keys()` 一致。

---

## 4. 落点字段

### 4.1 允许集

工具只允许 tag 影响以下字段类:

| 字段类 | 涉及表 | 字段 |
|---|---|---|
| 切片组成 (`slice`) | `ActvSoccerLevelCfg` | `SliceList` |
| AI/难度/Modifier (`ai`) | `ActvSoccerLevelCfg` / `ActvSoccerSliceAiCfg` | `AiProfileID` / `ModifierID`(注意 SliceAi 行按 `SliceID` 定位,见 §4.3) |
| 对手·阈值·门票 (`level`) | `ActvSoccerLevelCfg` | `OpponentTeamID` / `OpponentTeamStar` / `WinThreshold` / `DrawThreshold` / `TicketCost` / `IsTutorial` |

**禁止 tag 影响**:其余所有字段(SliceInstanceCfg / SlicePresetCfg / EnemyAiCfg / AiProfileCfg / AiModifierCfg / TeamCfg / SeasonCfg 都按 tier 默认全量生成,不被 tag 改写;Modifier 的修改只发生在该 level 引用的 SliceAi 行)。

### 4.2 作用粒度

**单关范围**:每行 tag 仅作用于该 `level_id` 对应的 `LevelCfg` 行 + 该 LevelCfg `SliceList` 引用的 `SliceAiCfg` 行。不做粒度叠加。

### 4.3 SliceAi 行定位策略

- 同一 SliceID(库实例)被多个 level 引用时,**`extreme_keeper` / `no_modifier` / `narrow_angle` 不能直接改 SliceAi 行**(会污染其他 level)。
- 解决方案:工具检测到此类 tag 时,**在 SliceAiCfg 中追加一行**,`SliceID` 不变、`AiProfileID/ModifierID` 改写,新行 ID 段 = `9000 + level_id*10 + 索引`,并把 LevelCfg 的 SliceList 中对应位置改为指向**新增的虚拟 SliceID**(为避免污染,新增 SliceInstanceCfg 行复制库行,ID 段 = `9000 + level_id*10 + 索引`,只改 ID,其余字段全继承)。
- 副作用:加 tag 的关会增加少量 SliceInstance/SliceAi 行,但不影响其他关。

### 4.4 叠加顺序

固定:**tier 默认行 → 按 Tags 列从左到右逐 tag 调用 patch**。互斥组校验在加载时先做,不存在「先冲突后处理」。

---

## 5. 冲突策略

- **互斥组**:`TagDef.MutexGroup` 同名的 tag 同关共存 → 报错。
- **未注册 tag**:报错。
- **错误格式**:统一收集所有错误,一次性打印 `[level_id, tags, reason]` 表后非零退出。不做警告降级。

---

## 6. 输出形态

### 6.1 与现有生成器关系

**另起生成器**,只生成关卡相关 8 表;与 `generate_activity_soccer_test_config.py` 完全独立。

### 6.2 输出范围(关卡产物族 9 表)

`ActvSoccerSeasonCfg` / `ActvSoccerLevelCfg` / `ActvSoccerSlicePresetCfg` / `ActvSoccerSliceInstanceCfg` / `ActvSoccerSliceAiCfg` / `ActvSoccerAiProfileCfg` / `ActvSoccerEnemyAiCfg` / `ActvSoccerAiModifierCfg` / `ActvSoccerTeamCfg`。

其中 Preset / AiProfile / EnemyAi / AiModifier / Team / Season 直接复用主生成器 `_build_*` 函数、不被 tag 改写;LevelCfg / SliceInstanceCfg / SliceAiCfg 三表受 tag 影响(SliceInstanceCfg / SliceAiCfg 的影响仅以 `9xxx` 段追加方式发生,见 §4.3)。

### 6.3 输出路径

`output/test-config/level-tags/ActivitySoccer.LevelTagged.xlsx`

写出策略:文件被占用时回退 `*.LevelTagged.generated.xlsx`(沿用现有主生成器约定)。

---

## 7. 校验

加载阶段(读输入即跑):

- LevelTagCfg.xlsx 必须存在,否则报错。
- `LevelTags` 页 ID 列 = 1..500 完整且无重复;`Round` / `LevelInRound` / `Tier` 与 ID 一致(给策划手抖兜底)。
- `TagDef.Tag` 集合 == `level_tag_lib.TAG_REGISTRY.keys()`(双源一致校验)。
- 每行 Tags 中所有 tag ∈ TAG_REGISTRY,否则报错。
- 同行 tag 的互斥组校验。

生成阶段(全部 patch 后跑):

- 每关 `0 < DrawThreshold < WinThreshold ≤ 切片数`,否则报错。
- 每个 `LevelCfg.SliceList` 内的 ID ∈ `SliceInstanceCfg`(含新增的 9xxx 行)。
- 每个 `SliceAiCfg.SliceID` ∈ `SliceInstanceCfg`。
- `LevelCfg.AiProfileID` ∈ {1001..1010}。

报告:

- stdout 摘要(总关数 / 贴 tag 关数 / 各 tag 命中数 / 校验结果)。
- `output/test-config/level-tags/level-tag-summary.json`(机读)。
- 退出码:0=ok / 1=校验失败 / 2=输入错。

---

## 8. 实现拆分

```
output/test-config/level-tags/
├── level_tag_lib.py                    # tag 注册器 + patch 函数(纯逻辑)
├── apply_level_tags.py                 # 入口:读 xlsx → patch → 写产物
├── generate_level_tag_template.py      # 一次性模板生成器
└── LevelTagCfg.xlsx                    # 策划填表入口(由模板脚本生成,允许 git 跟踪)
```

### 8.1 `level_tag_lib.py` 接口

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class TagSpec:
    name: str
    affects: tuple[str, ...]      # ('slice',) / ('ai',) / ('level',)
    mutex_group: str | None
    description: str
    patch: Callable[..., None]    # 见 PatchContext

@dataclass
class PatchContext:
    level_row: dict               # ActvSoccerLevelCfg 行(可改)
    slice_ai_rows: list[dict]     # 该 level SliceList 对应 SliceAiCfg 行(可改/可追加)
    slice_instance_rows: list[dict]  # 同上 SliceInstanceCfg 行(可追加)
    new_id_alloc: Callable[[], int]  # 9xxx 段 ID 分配器
    level_in_round: int
    tier: int
    library: dict                 # 只读:120 库实例 / 18 preset / 默认 SliceAi 行索引

TAG_REGISTRY: dict[str, TagSpec] = {}

def register(spec: TagSpec) -> None: ...
```

### 8.2 `apply_level_tags.py` 编排

1. 加载默认数据:从 `generate_activity_soccer_test_config.py` 直接 `import` `_build_levels / _build_seasons / _build_instance_library / _slice_ai_for_library / _build_ai_profiles / _build_enemy_ai / _build_ai_modifiers / _build_theme_teams / LcRegistry` 等成员;构造一个独立 `LcRegistry()` 实例传入 `_build_levels(lc) / _build_seasons(lc)`,避免污染主生成器输出。语言行(LcRegistry 累积)在本工具产物中**不写出**(本工具产物不含 LanguageCfg 表,语言由主生成器单独维护)。
2. 加载 `LevelTagCfg.xlsx`,做加载阶段全量校验。
3. 对每行 Tags 不为空的 level,按上下文 patch。
4. 跑生成阶段校验。
5. 写关卡产物族 9 表 xlsx + summary.json。
6. 打印 stdout 摘要 + 退出码。

### 8.3 `generate_level_tag_template.py`

- 读 `_build_levels` 默认行,生成 500 行的 `LevelTagCfg.xlsx`,Tags / Note 列留空。
- `TagDef` 页根据 `level_tag_lib.TAG_REGISTRY` 全量导出。
- 文件已存在时**默认拒绝覆盖**(避免吃掉策划已贴的 tag),需 `--force` 才覆盖;但允许 `--sync-tagdef` 仅刷新 TagDef 页(配合词表演进)。

---

## 9. 边界与已知约束

- 主生成器 `generate_activity_soccer_test_config.py` 改动:**零**。本工具完全独立。
- 主生成器与本工具产物的差异:本工具仅出关卡产物族 9 表;`ActivitySoccer.xlsx` 与 `ActivitySoccer.LevelTagged.xlsx` 之间合并由后续 config-table-editor / 主流程负责,不在本 spec 范围。
- 美术资源(KitKey / BadgeKey)不被 tag 影响。
- 9xxx 段 ID 与现有 ID 段(101-208 试训/引导、311-1062 库实例)不冲突,且与 SliceAi 3001-3006/3100+ 段、Modifier 4001-4007 段、EnemyAi 2001-2043 段、AiProfile 1001-1010 段都不冲突。

---

## 10. 验收

- ✅ 不传 LevelTagCfg.xlsx 时报错,退出码 2。
- ✅ 全空 Tags 表跑通后产物 = 主生成器关卡产物族 9 表(逐字段 diff 一致)。
- ✅ 至少一个互斥组 tag 同行存在时报错,退出码 1。
- ✅ 至少一个未注册 tag 时报错,退出码 1。
- ✅ 至少 5 个 tag(每类至少 1)在样例关上 patch 后产物可读、引用完整,退出码 0。
- ✅ summary.json 含每个 tag 的命中关 ID 列表。
