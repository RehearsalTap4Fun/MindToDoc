# 关卡 Tag 配置工具 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让策划在 `LevelTagCfg.xlsx` 单关贴语义 tag 后,自动生成 9 表关卡产物族 xlsx,基线复用主生成器 tier 默认。

**Architecture:** 三层目录拆分 —— `level_tag_lib.py`(tag 注册器 + patch 函数,纯逻辑) / `apply_level_tags.py`(读 xlsx → patch → 写 xlsx + summary.json) / `generate_level_tag_template.py`(一次性生成空 LevelTagCfg.xlsx 模板)。tag patch 通过追加 9xxx 段虚拟 SliceInstance/SliceAi 行实现单关隔离。

**Tech Stack:** Python 3.10+ / openpyxl / pytest;直接 import 主生成器 `_build_*` 函数复用 tier 模板。

**Spec:** `docs/superpowers/specs/2026-06-17-worldcup-level-config-tool-design.md`

---

## 文件结构

| 路径 | 职责 |
|---|---|
| `output/test-config/level-tags/level_tag_lib.py` | TagSpec / PatchContext dataclass + TAG_REGISTRY + 16 个 tag patch 函数 |
| `output/test-config/level-tags/apply_level_tags.py` | 主入口:加载默认 + 读 xlsx + 校验 + patch + 写产物 |
| `output/test-config/level-tags/generate_level_tag_template.py` | 一次性生成 `LevelTagCfg.xlsx`(LevelTags 500 行 + TagDef 词表导出) |
| `output/test-config/level-tags/__init__.py` | 空文件,使该目录可被 import |
| `output/test-config/level-tags/tests/__init__.py` | 空 |
| `output/test-config/level-tags/tests/test_level_tag_lib.py` | 词表 / patch 函数单元测试 |
| `output/test-config/level-tags/tests/test_apply.py` | 编排逻辑(加载/校验/输出)端到端测试 |
| `output/test-config/level-tags/tests/test_template.py` | 模板生成器测试 |
| `output/test-config/level-tags/LevelTagCfg.xlsx` | 由 `generate_level_tag_template.py` 生成,纳入 git |
| `output/test-config/level-tags/ActivitySoccer.LevelTagged.xlsx` | 产物,**不**纳入 git(加 .gitignore) |
| `output/test-config/level-tags/level-tag-summary.json` | 机读摘要,**不**纳入 git |

---

## Task 1: 目录脚手架 + .gitignore

**Files:**
- Create: `output/test-config/level-tags/__init__.py`
- Create: `output/test-config/level-tags/tests/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: 创建空 __init__.py 两份**

```bash
mkdir -p output/test-config/level-tags/tests
: > output/test-config/level-tags/__init__.py
: > output/test-config/level-tags/tests/__init__.py
```

- [ ] **Step 2: 在仓库根 .gitignore 追加产物忽略**

```
# 关卡 tag 工具产物(由 apply_level_tags.py 生成)
output/test-config/level-tags/ActivitySoccer.LevelTagged.xlsx
output/test-config/level-tags/ActivitySoccer.LevelTagged.generated.xlsx
output/test-config/level-tags/level-tag-summary.json
```

- [ ] **Step 3: 验证主生成器仍可 import(冒烟)**

Run:
```bash
python -c "import sys; sys.path.insert(0,'output/test-config'); from generate_activity_soccer_test_config import _build_levels, _build_seasons, _build_instance_library, _slice_ai_for_library, _build_ai_profiles, _build_enemy_ai, _build_ai_modifiers, _build_theme_teams, _build_presets, LcRegistry; print('import ok')"
```

Expected stdout: `import ok`

- [ ] **Step 4: Commit**

```bash
git add output/test-config/level-tags/__init__.py output/test-config/level-tags/tests/__init__.py .gitignore
git commit -m "chore: 关卡 tag 工具目录脚手架 + 产物 gitignore"
```

---

## Task 2: level_tag_lib.py 骨架(TagSpec / PatchContext / register / TAG_REGISTRY)

**Files:**
- Create: `output/test-config/level-tags/level_tag_lib.py`
- Create: `output/test-config/level-tags/tests/test_level_tag_lib.py`

- [ ] **Step 1: 写失败测试 —— register/TAG_REGISTRY 行为**

`output/test-config/level-tags/tests/test_level_tag_lib.py`:
```python
import importlib

def test_registry_starts_empty_then_accepts_register():
    lib = importlib.import_module("level_tag_lib")
    importlib.reload(lib)
    assert lib.TAG_REGISTRY == {}

    def noop_patch(ctx):
        pass

    spec = lib.TagSpec(
        name="foo",
        affects=("slice",),
        mutex_group=None,
        description="测试",
        patch=noop_patch,
    )
    lib.register(spec)
    assert "foo" in lib.TAG_REGISTRY
    assert lib.TAG_REGISTRY["foo"].mutex_group is None


def test_register_duplicate_raises():
    lib = importlib.import_module("level_tag_lib")
    importlib.reload(lib)

    def noop(ctx):
        pass

    spec = lib.TagSpec("dup", ("slice",), None, "x", noop)
    lib.register(spec)
    try:
        lib.register(spec)
    except ValueError as e:
        assert "dup" in str(e)
    else:
        raise AssertionError("expected ValueError on duplicate register")
```

- [ ] **Step 2: 跑测试看红**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_level_tag_lib.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'level_tag_lib'`

- [ ] **Step 3: 实现 lib 骨架**

`output/test-config/level-tags/level_tag_lib.py`:
```python
# -*- coding: utf-8 -*-
"""关卡 tag 词表与 patch 函数注册器。

每个 tag 在本文件 register() 注册到 TAG_REGISTRY,patch 函数在 PatchContext
上做单关 patch。apply_level_tags.py 加载 LevelTagCfg.xlsx 后按 Tags 列查表执行。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class PatchContext:
    """单关 patch 上下文,patch 函数读写本对象的 mutable 字段。"""
    level_row: dict
    slice_ai_rows: list[dict]            # 该 level SliceList 对应的 SliceAi 行(可改/追加)
    slice_instance_rows: list[dict]      # 该 level SliceList 引用的 SliceInstance 行(可追加)
    new_id_alloc: Callable[[], int]      # 9xxx 段虚拟 ID 分配器
    level_in_round: int
    tier: int
    library: dict                        # 只读快照:{'instances':..., 'slice_ais':..., 'tier_specs':...}


@dataclass
class TagSpec:
    name: str
    affects: tuple[str, ...]             # ('slice',) / ('ai',) / ('level',) 子集
    mutex_group: str | None
    description: str
    patch: Callable[[PatchContext], None]


TAG_REGISTRY: dict[str, TagSpec] = {}


def register(spec: TagSpec) -> None:
    """注册 tag,重复 name 直接报错。"""
    if spec.name in TAG_REGISTRY:
        raise ValueError(f"重复注册 tag: {spec.name}")
    TAG_REGISTRY[spec.name] = spec
```

- [ ] **Step 4: 跑测试看绿**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_level_tag_lib.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add output/test-config/level-tags/level_tag_lib.py output/test-config/level-tags/tests/test_level_tag_lib.py
git commit -m "feat(level-tags): 添加 TagSpec/PatchContext 与 TAG_REGISTRY 骨架"
```

---

## Task 3: 注册 5 个 level-only tag(boss / must_win / lenient / free_run / tutorial)

**Files:**
- Modify: `output/test-config/level-tags/level_tag_lib.py`
- Modify: `output/test-config/level-tags/tests/test_level_tag_lib.py`

这一批只改 `level_row` 标量字段,不动 SliceList/SliceAi,作为 patch 流水跑通的最小验证。

- [ ] **Step 1: 写 5 个 patch 的失败测试**

追加到 `tests/test_level_tag_lib.py`:
```python
def _make_ctx(slice_count=4, tier=5, level_in_round=5):
    """构造一个最小可用的 PatchContext,默认 slice_count=4 便于阈值断言。"""
    import importlib, level_tag_lib as lib
    importlib.reload(lib)
    # 触发后续 register 调用(在测试里 import 整个模块的 _register_*)
    from level_tag_lib import PatchContext
    return PatchContext(
        level_row={
            "ID": 250, "IsTutorial": 0,
            "SliceList": "[541,551,561,511]",
            "AiProfileID": 1005, "WinThreshold": 3, "DrawThreshold": 2,
            "TicketCost": 1, "OpponentTeamID": 3025, "OpponentTeamStar": 3,
            "SeasonID": 25, "Remark": "",
        },
        slice_ai_rows=[],
        slice_instance_rows=[],
        new_id_alloc=lambda: 99999,
        level_in_round=level_in_round,
        tier=tier,
        library={"slice_count": slice_count},
    )


def test_boss_sets_star5_and_full_win():
    import importlib, level_tag_lib as lib
    importlib.reload(lib)
    lib._register_level_only_tags()  # 由实现侧暴露
    ctx = _make_ctx()
    lib.TAG_REGISTRY["boss"].patch(ctx)
    assert ctx.level_row["OpponentTeamStar"] == 5
    assert ctx.level_row["WinThreshold"] == 4   # = slice_count
    assert ctx.level_row["DrawThreshold"] == 3


def test_must_win_pushes_thresholds():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["must_win"].patch(ctx)
    assert ctx.level_row["WinThreshold"] == 4
    assert ctx.level_row["DrawThreshold"] == 3


def test_lenient_lowers_thresholds():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags()
    ctx = _make_ctx(slice_count=5)
    lib.TAG_REGISTRY["lenient"].patch(ctx)
    # ceil(5*0.4)=2
    assert ctx.level_row["WinThreshold"] == 2
    assert ctx.level_row["DrawThreshold"] == 1


def test_free_run_zeros_ticket():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["free_run"].patch(ctx)
    assert ctx.level_row["TicketCost"] == 0


def test_tutorial_marks_and_swaps_slices():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["tutorial"].patch(ctx)
    assert ctx.level_row["IsTutorial"] == 1
    assert ctx.level_row["TicketCost"] == 0
    assert ctx.level_row["SliceList"] == "[201,202,203]"
```

- [ ] **Step 2: 跑测试看红**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_level_tag_lib.py -v -k "boss or must_win or lenient or free_run or tutorial"`
Expected: FAIL with `AttributeError: module 'level_tag_lib' has no attribute '_register_level_only_tags'`

- [ ] **Step 3: 实现 5 个 tag**

追加到 `level_tag_lib.py` 末尾:
```python
import json
import math


def _slice_count_of(level_row: dict) -> int:
    return len(json.loads(level_row["SliceList"]))


def _patch_boss(ctx: PatchContext) -> None:
    n = _slice_count_of(ctx.level_row)
    ctx.level_row["OpponentTeamStar"] = 5
    ctx.level_row["WinThreshold"] = n
    ctx.level_row["DrawThreshold"] = max(1, n - 1)


def _patch_must_win(ctx: PatchContext) -> None:
    n = _slice_count_of(ctx.level_row)
    ctx.level_row["WinThreshold"] = n
    ctx.level_row["DrawThreshold"] = max(1, n - 1)


def _patch_lenient(ctx: PatchContext) -> None:
    n = _slice_count_of(ctx.level_row)
    win = max(1, math.ceil(n * 0.4))
    ctx.level_row["WinThreshold"] = win
    ctx.level_row["DrawThreshold"] = max(1, win - 1)


def _patch_free_run(ctx: PatchContext) -> None:
    ctx.level_row["TicketCost"] = 0


def _patch_tutorial(ctx: PatchContext) -> None:
    ctx.level_row["IsTutorial"] = 1
    ctx.level_row["TicketCost"] = 0
    ctx.level_row["SliceList"] = "[201,202,203]"
    ctx.level_row["AiProfileID"] = 1001


def _register_level_only_tags() -> None:
    """注册不依赖 SliceAi/SliceInstance 的 5 个 level-only tag。
    幂等:重复调用先清同名条目再注册。"""
    for name in ("boss", "must_win", "lenient", "free_run", "tutorial"):
        TAG_REGISTRY.pop(name, None)
    register(TagSpec("boss", ("level",), None,
                     "对手 5 星 + 全胜阈值", _patch_boss))
    register(TagSpec("must_win", ("level",), "threshold",
                     "切片全胜才能赢", _patch_must_win))
    register(TagSpec("lenient", ("level",), "threshold",
                     "胜阈值降至 40%", _patch_lenient))
    register(TagSpec("free_run", ("level",), None,
                     "门票消耗 0", _patch_free_run))
    register(TagSpec("tutorial", ("level", "slice"), "tutorial",
                     "强制引导关 + [201,202,203]", _patch_tutorial))


_register_level_only_tags()
```

- [ ] **Step 4: 跑测试看绿**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_level_tag_lib.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add output/test-config/level-tags/level_tag_lib.py output/test-config/level-tags/tests/test_level_tag_lib.py
git commit -m "feat(level-tags): 注册 5 个 level-only tag (boss/must_win/lenient/free_run/tutorial)"
```

---

## Task 4: 注册 6 个 slice-类 tag(set_piece / corner_focus / gk_test / long_match / short_match / all_v2)

**Files:**
- Modify: `output/test-config/level-tags/level_tag_lib.py`
- Modify: `output/test-config/level-tags/tests/test_level_tag_lib.py`

slice 类 tag 改 `level_row.SliceList`,直接替换库实例 ID(无需 9xxx 段,因为 SliceInstance/SliceAi 的库实例所有关共享、不被改)。

**库实例 ID 编码回顾**:`tier*100 + type*10 + variant`,type:1 attack / 2 free_kick / 3 penalty / 4 corner / 5 throw_in / 6 goalkeep。

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_level_tag_lib.py`:
```python
def test_set_piece_inserts_freekick_and_penalty():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    # 默认 [541,551,561,511] 都不是 free_kick(52x) / penalty(53x)
    lib.TAG_REGISTRY["set_piece"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    assert any(s // 10 % 10 == 2 for s in sl), f"无 free_kick: {sl}"
    assert any(s // 10 % 10 == 3 for s in sl), f"无 penalty: {sl}"


def test_corner_focus_makes_last_corner_v2():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["corner_focus"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    last = sl[-1]
    assert last // 10 % 10 == 4 and last % 10 == 2, f"末位非 corner v2: {last}"


def test_gk_test_makes_last_goalkeep_v2():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["gk_test"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    last = sl[-1]
    assert last // 10 % 10 == 6 and last % 10 == 2, f"末位非 goalkeep v2: {last}"


def test_long_match_adds_one_slice_capped_at_5():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx(slice_count=4)  # 默认 SliceList 是 4 个
    lib.TAG_REGISTRY["long_match"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    assert len(sl) == 5

    ctx2 = _make_ctx(slice_count=5)
    ctx2.level_row["SliceList"] = "[541,551,561,511,521]"
    lib.TAG_REGISTRY["long_match"].patch(ctx2)
    assert len(json.loads(ctx2.level_row["SliceList"])) == 5  # 上限 5


def test_short_match_removes_one_floor_at_2():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["short_match"].patch(ctx)
    assert len(json.loads(ctx.level_row["SliceList"])) == 3

    ctx2 = _make_ctx()
    ctx2.level_row["SliceList"] = "[541,551]"
    lib.TAG_REGISTRY["short_match"].patch(ctx2)
    assert len(json.loads(ctx2.level_row["SliceList"])) == 2  # 下限 2


def test_all_v2_flips_last_digit():
    import importlib, level_tag_lib as lib
    importlib.reload(lib); lib._register_level_only_tags(); lib._register_slice_tags()
    ctx = _make_ctx()
    lib.TAG_REGISTRY["all_v2"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    assert all(s % 10 == 2 for s in sl), f"非全 v2: {sl}"
```

> 注:测试文件顶部需 `import json`,首条 import 没加的话此时加。

- [ ] **Step 2: 跑测试看红**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_level_tag_lib.py -v -k "set_piece or corner_focus or gk_test or long_match or short_match or all_v2"`
Expected: 6 FAIL on `_register_slice_tags` 不存在

- [ ] **Step 3: 实现 6 个 slice tag**

追加到 `level_tag_lib.py` 末尾:
```python
def _slice_id(tier: int, stype: int, variant: int) -> int:
    return tier * 100 + stype * 10 + variant


def _slice_type(sid: int) -> int:
    return (sid // 10) % 10


def _patch_set_piece(ctx: PatchContext) -> None:
    sl = json.loads(ctx.level_row["SliceList"])
    has_fk = any(_slice_type(s) == 2 for s in sl)
    has_pk = any(_slice_type(s) == 3 for s in sl)
    if not has_fk:
        sl.append(_slice_id(ctx.tier, 2, 1))
    if not has_pk:
        sl.append(_slice_id(ctx.tier, 3, 1))
    if len(sl) > 5:
        sl = sl[:5]
    ctx.level_row["SliceList"] = json.dumps(sl)


def _patch_corner_focus(ctx: PatchContext) -> None:
    sl = json.loads(ctx.level_row["SliceList"])
    sl[-1] = _slice_id(ctx.tier, 4, 2)
    ctx.level_row["SliceList"] = json.dumps(sl)


def _patch_gk_test(ctx: PatchContext) -> None:
    sl = json.loads(ctx.level_row["SliceList"])
    sl[-1] = _slice_id(ctx.tier, 6, 2)
    ctx.level_row["SliceList"] = json.dumps(sl)


def _patch_long_match(ctx: PatchContext) -> None:
    sl = json.loads(ctx.level_row["SliceList"])
    if len(sl) >= 5:
        return
    # 选一个 SliceList 中没有的类型补充
    used_types = {_slice_type(s) for s in sl}
    for stype in (1, 2, 3, 4, 5, 6):
        if stype not in used_types:
            sl.append(_slice_id(ctx.tier, stype, 1))
            break
    else:
        sl.append(_slice_id(ctx.tier, 1, 1))
    ctx.level_row["SliceList"] = json.dumps(sl)


def _patch_short_match(ctx: PatchContext) -> None:
    sl = json.loads(ctx.level_row["SliceList"])
    if len(sl) > 2:
        sl = sl[:-1]
    ctx.level_row["SliceList"] = json.dumps(sl)


def _patch_all_v2(ctx: PatchContext) -> None:
    sl = json.loads(ctx.level_row["SliceList"])
    sl = [(s // 10) * 10 + 2 for s in sl]
    ctx.level_row["SliceList"] = json.dumps(sl)


def _register_slice_tags() -> None:
    for name in ("set_piece", "corner_focus", "gk_test",
                 "long_match", "short_match", "all_v2"):
        TAG_REGISTRY.pop(name, None)
    register(TagSpec("set_piece", ("slice",), None,
                     "保证至少 1 free_kick + 1 penalty", _patch_set_piece))
    register(TagSpec("corner_focus", ("slice",), None,
                     "末位强制 corner v2", _patch_corner_focus))
    register(TagSpec("gk_test", ("slice",), None,
                     "末位强制 goalkeep v2", _patch_gk_test))
    register(TagSpec("long_match", ("slice",), "length",
                     "切片数 +1(上限 5)", _patch_long_match))
    register(TagSpec("short_match", ("slice",), "length",
                     "切片数 -1(下限 2)", _patch_short_match))
    register(TagSpec("all_v2", ("slice",), None,
                     "SliceList 全切到 v2 复合变体", _patch_all_v2))


_register_slice_tags()
```

- [ ] **Step 4: 跑测试看绿**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_level_tag_lib.py -v`
Expected: 13 passed(7 旧 + 6 新)

- [ ] **Step 5: Commit**

```bash
git add output/test-config/level-tags/level_tag_lib.py output/test-config/level-tags/tests/test_level_tag_lib.py
git commit -m "feat(level-tags): 注册 6 个 slice 类 tag (set_piece/corner_focus/gk_test/long_match/short_match/all_v2)"
```

---

## Task 5: 注册 5 个 ai-类 tag(hard_plus / easy_minus / extreme_keeper / no_modifier / narrow_angle)

**Files:**
- Modify: `output/test-config/level-tags/level_tag_lib.py`
- Modify: `output/test-config/level-tags/tests/test_level_tag_lib.py`

`hard_plus / easy_minus` 改 `level_row.AiProfileID`(单关 LevelCfg 级,不污染共享 SliceAi)。
`extreme_keeper / no_modifier / narrow_angle` 必须改 SliceAi.ModifierID,但同 SliceID 被多关共享,故走 9xxx 段虚拟实例追加(spec §4.3)。

**新 ID 段约定**:`virt_id = 90000 + level_id*10 + slot_index`(slot_index = SliceList 中位置 0-4)。
分配器 `new_id_alloc` 由 apply 层注入,lib 不持状态。

- [ ] **Step 1: 写 ai-类失败测试**

追加到 `tests/test_level_tag_lib.py`:
```python
def _make_ctx_with_slice_ai():
    """构造带 SliceList 对应 SliceAi 行的 ctx,模拟 apply 层的现实输入。"""
    import importlib, level_tag_lib as lib
    importlib.reload(lib)
    lib._register_level_only_tags(); lib._register_slice_tags(); lib._register_ai_tags()
    counter = {"v": 90000}
    def alloc():
        counter["v"] += 1
        return counter["v"]
    sl_ids = [541, 551, 561, 511]
    return lib.PatchContext(
        level_row={
            "ID": 250, "IsTutorial": 0,
            "SliceList": json.dumps(sl_ids),
            "AiProfileID": 1005, "WinThreshold": 3, "DrawThreshold": 2,
            "TicketCost": 1, "OpponentTeamID": 3025, "OpponentTeamStar": 3,
            "SeasonID": 25, "Remark": "",
        },
        slice_ai_rows=[
            {"ID": 3100+i, "SliceID": sid, "AiProfileID": 1005,
             "GoalkeeperAiID": 2031, "DefenderAiID": 2032, "ShooterAiID": 0,
             "ModifierID": 4002, "IsGuideAi": 0, "RewindRandom": 1,
             "OverrideReactionTimeMs": 950, "Remark": ""}
            for i, sid in enumerate(sl_ids)
        ],
        slice_instance_rows=[
            {"ID": sid, "SliceType": "x", "PresetID": 1,
             "OverrideOperableAngle": 32.0, "ObjectiveType": "score",
             "ExtraObjectives": "[]", "Modifiers": "[]", "Remark": ""}
            for sid in sl_ids
        ],
        new_id_alloc=alloc, level_in_round=5, tier=5,
        library={"slice_count": 4},
    )


def test_hard_plus_bumps_profile_and_star():
    ctx = _make_ctx_with_slice_ai()
    import level_tag_lib as lib
    lib.TAG_REGISTRY["hard_plus"].patch(ctx)
    assert ctx.level_row["AiProfileID"] == 1006
    assert ctx.level_row["OpponentTeamStar"] == 4


def test_hard_plus_caps_at_1010_and_star5():
    ctx = _make_ctx_with_slice_ai()
    ctx.level_row["AiProfileID"] = 1010
    ctx.level_row["OpponentTeamStar"] = 5
    import level_tag_lib as lib
    lib.TAG_REGISTRY["hard_plus"].patch(ctx)
    assert ctx.level_row["AiProfileID"] == 1010
    assert ctx.level_row["OpponentTeamStar"] == 5


def test_easy_minus_floors_at_1001_and_star1():
    ctx = _make_ctx_with_slice_ai()
    ctx.level_row["AiProfileID"] = 1001
    ctx.level_row["OpponentTeamStar"] = 1
    import level_tag_lib as lib
    lib.TAG_REGISTRY["easy_minus"].patch(ctx)
    assert ctx.level_row["AiProfileID"] == 1001
    assert ctx.level_row["OpponentTeamStar"] == 1


def test_extreme_keeper_appends_virtual_slice_ai_and_instance():
    ctx = _make_ctx_with_slice_ai()
    instances_before = len(ctx.slice_instance_rows)
    slice_ais_before = len(ctx.slice_ai_rows)
    import level_tag_lib as lib
    lib.TAG_REGISTRY["extreme_keeper"].patch(ctx)
    sl = json.loads(ctx.level_row["SliceList"])
    assert all(s >= 90000 for s in sl), f"SliceList 仍含原 ID: {sl}"
    assert len(ctx.slice_instance_rows) == instances_before + len(sl)
    assert len(ctx.slice_ai_rows) == slice_ais_before + len(sl)
    new_ais = ctx.slice_ai_rows[slice_ais_before:]
    assert all(r["ModifierID"] == 4005 for r in new_ais)


def test_no_modifier_zeroes_modifier_in_virtual_rows():
    ctx = _make_ctx_with_slice_ai()
    import level_tag_lib as lib
    lib.TAG_REGISTRY["no_modifier"].patch(ctx)
    new_ais = [r for r in ctx.slice_ai_rows if r["ID"] >= 90000]
    assert len(new_ais) > 0
    assert all(r["ModifierID"] == 0 for r in new_ais)


def test_narrow_angle_sets_4006():
    ctx = _make_ctx_with_slice_ai()
    import level_tag_lib as lib
    lib.TAG_REGISTRY["narrow_angle"].patch(ctx)
    new_ais = [r for r in ctx.slice_ai_rows if r["ID"] >= 90000]
    assert all(r["ModifierID"] == 4006 for r in new_ais)
```

- [ ] **Step 2: 跑测试看红**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_level_tag_lib.py -v -k "hard_plus or easy_minus or extreme_keeper or no_modifier or narrow_angle"`
Expected: 6 FAIL on `_register_ai_tags` 不存在

- [ ] **Step 3: 实现 5 个 ai tag + 9xxx 虚拟 ID 公共逻辑**

追加到 `level_tag_lib.py` 末尾:
```python
def _patch_hard_plus(ctx: PatchContext) -> None:
    ctx.level_row["AiProfileID"] = min(1010, ctx.level_row["AiProfileID"] + 1)
    ctx.level_row["OpponentTeamStar"] = min(5, ctx.level_row["OpponentTeamStar"] + 1)


def _patch_easy_minus(ctx: PatchContext) -> None:
    ctx.level_row["AiProfileID"] = max(1001, ctx.level_row["AiProfileID"] - 1)
    ctx.level_row["OpponentTeamStar"] = max(1, ctx.level_row["OpponentTeamStar"] - 1)


def _virtualize_slice_modifier(ctx: PatchContext, new_modifier_id: int) -> None:
    """对 SliceList 中每个槽位:复制原 SliceInstance + 原 SliceAi 各一份(用 new_id_alloc),
    新 SliceAi.ModifierID = new_modifier_id,SliceList 改指向新 instance ID。"""
    sl = json.loads(ctx.level_row["SliceList"])
    ai_by_sid = {r["SliceID"]: r for r in ctx.slice_ai_rows}
    inst_by_id = {r["ID"]: r for r in ctx.slice_instance_rows}
    new_sl: list[int] = []
    for original_sid in sl:
        new_id = ctx.new_id_alloc()
        if original_sid in inst_by_id:
            new_inst = dict(inst_by_id[original_sid])
            new_inst["ID"] = new_id
            new_inst["Remark"] = (new_inst.get("Remark", "") + f" tag-virtual lvl{ctx.level_row['ID']}").strip()
            ctx.slice_instance_rows.append(new_inst)
        if original_sid in ai_by_sid:
            new_ai = dict(ai_by_sid[original_sid])
            new_ai["ID"] = new_id
            new_ai["SliceID"] = new_id
            new_ai["ModifierID"] = new_modifier_id
            new_ai["Remark"] = (new_ai.get("Remark", "") + f" tag-virtual lvl{ctx.level_row['ID']}").strip()
            ctx.slice_ai_rows.append(new_ai)
        new_sl.append(new_id)
    ctx.level_row["SliceList"] = json.dumps(new_sl)


def _patch_extreme_keeper(ctx: PatchContext) -> None:
    _virtualize_slice_modifier(ctx, 4005)


def _patch_no_modifier(ctx: PatchContext) -> None:
    _virtualize_slice_modifier(ctx, 0)


def _patch_narrow_angle(ctx: PatchContext) -> None:
    _virtualize_slice_modifier(ctx, 4006)


def _register_ai_tags() -> None:
    for name in ("hard_plus", "easy_minus", "extreme_keeper",
                 "no_modifier", "narrow_angle"):
        TAG_REGISTRY.pop(name, None)
    register(TagSpec("hard_plus", ("ai",), "difficulty",
                     "AiProfile +1 + OpponentStar +1", _patch_hard_plus))
    register(TagSpec("easy_minus", ("ai",), "difficulty",
                     "AiProfile -1 + OpponentStar -1", _patch_easy_minus))
    register(TagSpec("extreme_keeper", ("ai",), "modifier",
                     "ModifierID 强制 4005", _patch_extreme_keeper))
    register(TagSpec("no_modifier", ("ai",), "modifier",
                     "ModifierID 强制 0", _patch_no_modifier))
    register(TagSpec("narrow_angle", ("ai",), "modifier",
                     "ModifierID 强制 4006", _patch_narrow_angle))


_register_ai_tags()
```

- [ ] **Step 4: 跑测试看绿**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_level_tag_lib.py -v`
Expected: 19 passed

- [ ] **Step 5: 验证 TAG_REGISTRY 全 16 项**

Run:
```bash
cd output/test-config/level-tags && python -c "import level_tag_lib as lib; assert len(lib.TAG_REGISTRY) == 16, len(lib.TAG_REGISTRY); print(sorted(lib.TAG_REGISTRY.keys()))"
```

Expected: 16 个 tag 字典序

- [ ] **Step 6: Commit**

```bash
git add output/test-config/level-tags/level_tag_lib.py output/test-config/level-tags/tests/test_level_tag_lib.py
git commit -m "feat(level-tags): 注册 5 个 ai 类 tag + 9xxx 段虚拟 SliceInstance/SliceAi 机制"
```

---

## Task 6: generate_level_tag_template.py(一次性生成 LevelTagCfg.xlsx 模板)

**Files:**
- Create: `output/test-config/level-tags/generate_level_tag_template.py`
- Create: `output/test-config/level-tags/tests/test_template.py`

模板含两页:`LevelTags` 500 行(Tags/Note 列空)+ `TagDef` 词表。

- [ ] **Step 1: 写模板生成器测试**

`tests/test_template.py`:
```python
import importlib
import math
import sys
from pathlib import Path

import openpyxl


def _run_template(tmp_path: Path):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # output/test-config/
    import generate_level_tag_template as g
    importlib.reload(g)
    out = tmp_path / "LevelTagCfg.xlsx"
    g.generate(out)
    return out


def test_template_has_500_level_rows(tmp_path):
    out = _run_template(tmp_path)
    wb = openpyxl.load_workbook(out)
    assert "LevelTags" in wb.sheetnames
    ws = wb["LevelTags"]
    # 表头 8 行约定(对齐主生成器 make_sheet),数据从第 9 行起
    data_rows = [r for r in ws.iter_rows(min_row=9, values_only=True) if r[0] is not None]
    assert len(data_rows) == 500
    # 第 1 关
    first = data_rows[0]
    assert first[0] == 1 and first[1] == 1 and first[2] == 1 and first[3] == 1
    # 第 500 关:Round=50, LevelInRound=10, Tier=10
    last = data_rows[-1]
    assert last[0] == 500 and last[1] == 50 and last[2] == 10 and last[3] == 10


def test_template_tag_def_matches_registry(tmp_path):
    out = _run_template(tmp_path)
    wb = openpyxl.load_workbook(out)
    assert "TagDef" in wb.sheetnames
    ws = wb["TagDef"]
    rows = [r for r in ws.iter_rows(min_row=9, values_only=True) if r[0]]
    tags_in_sheet = {r[0] for r in rows}
    import level_tag_lib as lib
    assert tags_in_sheet == set(lib.TAG_REGISTRY.keys())


def test_template_refuses_overwrite(tmp_path):
    out = _run_template(tmp_path)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import generate_level_tag_template as g
    try:
        g.generate(out)
    except FileExistsError as e:
        assert "force" in str(e).lower()
    else:
        raise AssertionError("expected FileExistsError on second call without force")


def test_template_force_overwrites(tmp_path):
    out = _run_template(tmp_path)
    import generate_level_tag_template as g
    g.generate(out, force=True)  # 不抛
```

- [ ] **Step 2: 跑测试看红**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_template.py -v`
Expected: ModuleNotFoundError on `generate_level_tag_template`

- [ ] **Step 3: 实现模板生成器**

`output/test-config/level-tags/generate_level_tag_template.py`:
```python
# -*- coding: utf-8 -*-
"""生成 LevelTagCfg.xlsx 模板:LevelTags 500 行 + TagDef 词表。

策划在 LevelTags.Tags 列贴 tag,空行表示该关走 tier 默认。
TagDef 页由 level_tag_lib.TAG_REGISTRY 全量导出,作为人读对照与互斥校验依据。
首次运行后,后续运行需 force=True 才覆盖,避免吃掉已贴 tag。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from openpyxl import Workbook

# 同目录的 level_tag_lib + 上级 generate_activity_soccer 都要 import
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import level_tag_lib  # noqa: E402

DEFAULT_OUT = HERE / "LevelTagCfg.xlsx"
ROUNDS_TOTAL = 50
LEVELS_PER_ROUND = 10


def _write_header(ws, fields: list[tuple[str, str, str]]) -> None:
    """主生成器约定:8 行表头(读取端/类型/字段名/server/4 行注释),数据从第 9 行起。"""
    for col_idx, (read, type_, field) in enumerate(fields, start=1):
        ws.cell(1, col_idx, read)
        ws.cell(2, col_idx, type_)
        ws.cell(3, col_idx, field)
        ws.cell(4, col_idx, "")
        ws.cell(5, col_idx, "")
        ws.cell(6, col_idx, "")
        ws.cell(7, col_idx, "")
        ws.cell(8, col_idx, "")


def _build_level_tags_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("LevelTags")
    _write_header(ws, [
        ("cs", "int", "ID"),
        ("c", "int", "Round"),
        ("c", "int", "LevelInRound"),
        ("c", "int", "Tier"),
        ("c", "string", "Tags"),
        ("-", "string", "Note"),
    ])
    row_idx = 9
    for r in range(1, ROUNDS_TOTAL + 1):
        for j in range(1, LEVELS_PER_ROUND + 1):
            level_id = (r - 1) * LEVELS_PER_ROUND + j
            tier = math.ceil(r / 5)
            ws.cell(row_idx, 1, level_id)
            ws.cell(row_idx, 2, r)
            ws.cell(row_idx, 3, j)
            ws.cell(row_idx, 4, tier)
            ws.cell(row_idx, 5, "")
            ws.cell(row_idx, 6, "")
            row_idx += 1


def _build_tag_def_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("TagDef")
    _write_header(ws, [
        ("c", "string", "Tag"),
        ("c", "string", "Affects"),
        ("c", "string", "MutexGroup"),
        ("c", "string", "Description"),
    ])
    row_idx = 9
    for tag in sorted(level_tag_lib.TAG_REGISTRY.keys()):
        spec = level_tag_lib.TAG_REGISTRY[tag]
        ws.cell(row_idx, 1, spec.name)
        ws.cell(row_idx, 2, ",".join(spec.affects))
        ws.cell(row_idx, 3, spec.mutex_group or "")
        ws.cell(row_idx, 4, spec.description)
        row_idx += 1


def generate(out: Path = DEFAULT_OUT, force: bool = False) -> Path:
    out = Path(out)
    if out.exists() and not force:
        raise FileExistsError(
            f"{out} 已存在;加 force=True 覆盖(会丢失已贴 tag)"
        )
    wb = Workbook()
    wb.remove(wb.active)
    _build_level_tags_sheet(wb)
    _build_tag_def_sheet(wb)
    wb.save(out)
    return out


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()
    path = generate(args.out, force=args.force)
    print(f"模板生成: {path}")
```

- [ ] **Step 4: 跑测试看绿**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_template.py -v`
Expected: 4 passed

- [ ] **Step 5: 实际生成 LevelTagCfg.xlsx 入库**

Run:
```bash
cd output/test-config/level-tags && python generate_level_tag_template.py
```

Expected stdout: `模板生成: .../LevelTagCfg.xlsx`

- [ ] **Step 6: Commit(含模板 xlsx)**

```bash
git add output/test-config/level-tags/generate_level_tag_template.py \
        output/test-config/level-tags/tests/test_template.py \
        output/test-config/level-tags/LevelTagCfg.xlsx
git commit -m "feat(level-tags): 模板生成器 + LevelTagCfg.xlsx 初版(500 行 LevelTags + TagDef)"
```

---

## Task 7: apply_level_tags.py 加载层(读 xlsx + 加载阶段校验)

**Files:**
- Create: `output/test-config/level-tags/apply_level_tags.py`
- Create: `output/test-config/level-tags/tests/test_apply.py`

只做加载层和校验,不写产物。下个任务做 patch 编排,再下一个写 xlsx。

加载阶段校验项(spec §7):
1. LevelTagCfg.xlsx 必须存在
2. LevelTags 页 ID 列 = 1..500 完整无重复
3. Round/LevelInRound/Tier 与 ID 一致
4. TagDef.Tag 集合 == TAG_REGISTRY.keys()
5. 每行 Tags 中所有 tag ∈ TAG_REGISTRY
6. 同行 tag 互斥组校验

错误统一收集后一次性报错(`ValidationError` 携带列表)。

- [ ] **Step 1: 写加载层失败测试**

`tests/test_apply.py`:
```python
import importlib
import math
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook


HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))


def _make_minimal_xlsx(tmp_path: Path, *, tag_overrides: dict[int, str] | None = None,
                       break_id: bool = False, missing_tag_def: bool = False,
                       extra_tag_def: bool = False) -> Path:
    """构造一个最小可用的 LevelTagCfg.xlsx。"""
    import level_tag_lib  # noqa
    importlib.reload(level_tag_lib)
    import generate_level_tag_template as g
    importlib.reload(g)
    out = tmp_path / "LevelTagCfg.xlsx"
    g.generate(out)

    from openpyxl import load_workbook
    wb = load_workbook(out)
    ws = wb["LevelTags"]
    if tag_overrides:
        for level_id, tags_str in tag_overrides.items():
            row_idx = 9 + (level_id - 1)  # 数据从第 9 行起
            ws.cell(row_idx, 5, tags_str)
    if break_id:
        ws.cell(9, 1, 999)  # 把第 1 关 ID 改为 999

    td = wb["TagDef"]
    if missing_tag_def:
        # 删除最后一行(行 idx 9 + len(REGISTRY) - 1)
        td.delete_rows(9 + len(level_tag_lib.TAG_REGISTRY) - 1, 1)
    if extra_tag_def:
        td.cell(9 + len(level_tag_lib.TAG_REGISTRY), 1, "ghost_tag_xyz")
    wb.save(out)
    return out


def test_load_missing_file_raises(tmp_path):
    import apply_level_tags as app
    importlib.reload(app)
    with pytest.raises(FileNotFoundError):
        app.load_level_tag_cfg(tmp_path / "absent.xlsx")


def test_load_clean_file_returns_500_rows(tmp_path):
    out = _make_minimal_xlsx(tmp_path)
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    assert len(rows) == 500
    assert rows[0]["ID"] == 1
    assert rows[-1]["ID"] == 500
    assert rows[0]["Tags"] == []   # 空 tag 解析为空 list


def test_load_with_tags_parses_them(tmp_path):
    out = _make_minimal_xlsx(tmp_path, tag_overrides={
        100: "boss",
        200: "hard_plus, set_piece",
        300: "must_win,no_modifier",
    })
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    assert rows[99]["Tags"] == ["boss"]
    assert rows[199]["Tags"] == ["hard_plus", "set_piece"]
    assert rows[299]["Tags"] == ["must_win", "no_modifier"]


def test_validate_id_break(tmp_path):
    out = _make_minimal_xlsx(tmp_path, break_id=True)
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    with pytest.raises(app.ValidationError) as ei:
        app.validate_loaded(rows, td_tags=set(_registry_tags()))
    assert any("ID" in e for e in ei.value.errors)


def _registry_tags():
    import level_tag_lib as lib
    return list(lib.TAG_REGISTRY.keys())


def test_validate_unknown_tag(tmp_path):
    out = _make_minimal_xlsx(tmp_path, tag_overrides={42: "ghost_tag_xyz"})
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    with pytest.raises(app.ValidationError) as ei:
        app.validate_loaded(rows, td_tags=set(_registry_tags()))
    assert any("ghost_tag_xyz" in e for e in ei.value.errors)


def test_validate_mutex_violation(tmp_path):
    # hard_plus 与 easy_minus 同 mutex_group=difficulty
    out = _make_minimal_xlsx(tmp_path, tag_overrides={50: "hard_plus,easy_minus"})
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    with pytest.raises(app.ValidationError) as ei:
        app.validate_loaded(rows, td_tags=set(_registry_tags()))
    assert any("mutex" in e.lower() or "互斥" in e for e in ei.value.errors)


def test_validate_tag_def_drift(tmp_path):
    out = _make_minimal_xlsx(tmp_path, missing_tag_def=True)
    import apply_level_tags as app
    importlib.reload(app)
    td_tags = app.load_tag_def(out)
    import level_tag_lib as lib
    assert td_tags != set(lib.TAG_REGISTRY.keys())
```

- [ ] **Step 2: 跑测试看红**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_apply.py -v`
Expected: 7 FAIL on `apply_level_tags` 不存在

- [ ] **Step 3: 实现 apply_level_tags.py 加载层**

`output/test-config/level-tags/apply_level_tags.py`:
```python
# -*- coding: utf-8 -*-
"""关卡 tag 配置工具入口(加载 + 校验阶段)。

本文件负责加载、校验、patch 编排、xlsx 写出与 CLI 入口。
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import level_tag_lib  # noqa: E402

DEFAULT_INPUT = HERE / "LevelTagCfg.xlsx"
ROUNDS_TOTAL = 50
LEVELS_PER_ROUND = 10


@dataclass
class ValidationError(Exception):
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return "\n".join(self.errors) or "(no errors)"


def _parse_tags(cell_value) -> list[str]:
    if cell_value is None:
        return []
    s = str(cell_value).strip()
    if not s:
        return []
    return [t.strip() for t in s.replace(",", " ").split() if t.strip()]


def load_level_tag_cfg(path: Path) -> list[dict]:
    """读取 LevelTags 页,返回 500 行 dict 列表。Tags 字段已解析为 list[str]。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    wb = load_workbook(p, read_only=True)
    if "LevelTags" not in wb.sheetnames:
        raise ValueError(f"{p} 缺少 LevelTags 页")
    ws = wb["LevelTags"]
    rows: list[dict] = []
    for row in ws.iter_rows(min_row=9, values_only=True):
        if row[0] is None:
            continue
        rows.append({
            "ID": int(row[0]),
            "Round": int(row[1]) if row[1] is not None else 0,
            "LevelInRound": int(row[2]) if row[2] is not None else 0,
            "Tier": int(row[3]) if row[3] is not None else 0,
            "Tags": _parse_tags(row[4]),
            "Note": row[5] or "",
        })
    return rows


def load_tag_def(path: Path) -> set[str]:
    p = Path(path)
    wb = load_workbook(p, read_only=True)
    if "TagDef" not in wb.sheetnames:
        raise ValueError(f"{p} 缺少 TagDef 页")
    ws = wb["TagDef"]
    tags: set[str] = set()
    for row in ws.iter_rows(min_row=9, values_only=True):
        if row[0]:
            tags.add(str(row[0]))
    return tags


def validate_loaded(rows: list[dict], td_tags: set[str]) -> None:
    """加载阶段全量校验,错误统一收集后一次性抛出。"""
    errors: list[str] = []

    # 1. ID 完整性 1..500 + 唯一
    seen = set()
    for r in rows:
        if r["ID"] in seen:
            errors.append(f"ID 重复: {r['ID']}")
        seen.add(r["ID"])
    expected = set(range(1, ROUNDS_TOTAL * LEVELS_PER_ROUND + 1))
    missing = expected - seen
    extra = seen - expected
    if missing:
        errors.append(f"ID 缺失: {sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}")
    if extra:
        errors.append(f"ID 越界: {sorted(extra)}")

    # 2. Round/LevelInRound/Tier 一致性
    for r in rows:
        lid = r["ID"]
        if not (1 <= lid <= 500):
            continue
        expected_round = (lid - 1) // LEVELS_PER_ROUND + 1
        expected_lir = (lid - 1) % LEVELS_PER_ROUND + 1
        expected_tier = math.ceil(expected_round / 5)
        if r["Round"] != expected_round:
            errors.append(f"level {lid} Round 不一致: {r['Round']} vs {expected_round}")
        if r["LevelInRound"] != expected_lir:
            errors.append(f"level {lid} LevelInRound 不一致: {r['LevelInRound']} vs {expected_lir}")
        if r["Tier"] != expected_tier:
            errors.append(f"level {lid} Tier 不一致: {r['Tier']} vs {expected_tier}")

    # 3. TagDef 与 lib 注册表一致
    lib_tags = set(level_tag_lib.TAG_REGISTRY.keys())
    if td_tags != lib_tags:
        only_def = td_tags - lib_tags
        only_lib = lib_tags - td_tags
        if only_def:
            errors.append(f"TagDef 多余 tag(lib 未注册): {sorted(only_def)}")
        if only_lib:
            errors.append(f"lib 注册但 TagDef 缺少: {sorted(only_lib)}")

    # 4. 未注册 tag + 5. 互斥组冲突
    for r in rows:
        for tag in r["Tags"]:
            if tag not in level_tag_lib.TAG_REGISTRY:
                errors.append(f"level {r['ID']} 未知 tag: {tag}")
        groups: dict[str, list[str]] = {}
        for tag in r["Tags"]:
            spec = level_tag_lib.TAG_REGISTRY.get(tag)
            if spec and spec.mutex_group:
                groups.setdefault(spec.mutex_group, []).append(tag)
        for group, conflict in groups.items():
            if len(conflict) > 1:
                errors.append(f"level {r['ID']} mutex 组 {group} 冲突: {conflict}")

    if errors:
        raise ValidationError(errors)
```

- [ ] **Step 4: 跑测试看绿**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_apply.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add output/test-config/level-tags/apply_level_tags.py output/test-config/level-tags/tests/test_apply.py
git commit -m "feat(level-tags): apply 加载层 + 校验(ID 完整性/TagDef 漂移/未知 tag/互斥组)"
```

---

## Task 8: apply patch 编排 + 生成阶段校验

**Files:**
- Modify: `output/test-config/level-tags/apply_level_tags.py`
- Modify: `output/test-config/level-tags/tests/test_apply.py`

引入主生成器作为默认数据源,逐关 patch,再做生成阶段校验。

- [ ] **Step 1: 写 patch 编排测试**

追加到 `tests/test_apply.py`:
```python
def test_orchestrate_no_tags_returns_default_dataset(tmp_path):
    out = _make_minimal_xlsx(tmp_path)
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    td_tags = app.load_tag_def(out)
    app.validate_loaded(rows, td_tags=td_tags)
    dataset = app.build_dataset(rows)
    # 全空 tag 时,产物应等同主生成器的 _build_levels(独立 LcRegistry)
    assert len(dataset["levels"]) == 500
    assert len(dataset["seasons"]) == 50
    # SliceInstance 含 6 旧(101-203) + 120 库 = 126,无虚拟行
    assert len(dataset["slice_instances"]) == 126
    # 没有 9xxx 段虚拟 ID
    assert all(r["ID"] < 90000 for r in dataset["slice_instances"])


def test_orchestrate_boss_tag_changes_only_target_level(tmp_path):
    out = _make_minimal_xlsx(tmp_path, tag_overrides={250: "boss"})
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    td_tags = app.load_tag_def(out)
    app.validate_loaded(rows, td_tags=td_tags)
    dataset = app.build_dataset(rows)
    levels = {r["ID"]: r for r in dataset["levels"]}
    assert levels[250]["OpponentTeamStar"] == 5
    # 邻居关不变
    assert levels[251]["OpponentTeamStar"] != 5 or levels[251]["OpponentTeamStar"] == levels[259]["OpponentTeamStar"]


def test_orchestrate_extreme_keeper_appends_virtual_rows(tmp_path):
    out = _make_minimal_xlsx(tmp_path, tag_overrides={250: "extreme_keeper"})
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    td_tags = app.load_tag_def(out)
    app.validate_loaded(rows, td_tags=td_tags)
    dataset = app.build_dataset(rows)
    virt_inst = [r for r in dataset["slice_instances"] if r["ID"] >= 90000]
    virt_ai = [r for r in dataset["slice_ais"] if r["ID"] >= 90000]
    assert len(virt_inst) > 0 and len(virt_inst) == len(virt_ai)
    assert all(r["ModifierID"] == 4005 for r in virt_ai)
    # level 250 SliceList 全部指向 9xxx
    levels = {r["ID"]: r for r in dataset["levels"]}
    import json as _json
    assert all(s >= 90000 for s in _json.loads(levels[250]["SliceList"]))


def test_post_validate_catches_threshold_violation(tmp_path):
    # 故意构造一个 lenient + must_win 共存(它们没有同 mutex_group,
    # 但 lenient 后 must_win 会反过来,正好测连续 patch 的最终态)
    out = _make_minimal_xlsx(tmp_path, tag_overrides={250: "lenient,must_win"})
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    td_tags = app.load_tag_def(out)
    app.validate_loaded(rows, td_tags=td_tags)
    # build_dataset 应能跑通(must_win 写入有效阈值);post_validate 0 错
    dataset = app.build_dataset(rows)
    app.validate_dataset(dataset)  # 不抛
```

- [ ] **Step 2: 跑测试看红**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_apply.py -v -k "orchestrate or post_validate"`
Expected: 4 FAIL on `build_dataset` 不存在

- [ ] **Step 3: 实现 build_dataset + validate_dataset**

追加到 `apply_level_tags.py` 末尾:
```python
import json as _json


def _import_main_generator():
    """惰性导入主生成器,避免顶层 import 顺序污染。"""
    sys.path.insert(0, str(HERE.parent))  # output/test-config/
    import generate_activity_soccer_test_config as g  # noqa
    return g


def _build_default_dataset() -> dict:
    """复用主生成器构造默认数据集(独立 LcRegistry,语言行不写出)。"""
    g = _import_main_generator()
    lc = g.LcRegistry()
    presets = g._build_presets(lc)
    instances = g._build_instance_library()
    slice_ais = g._slice_ai_for_library(instances)
    levels = g._build_levels(lc)
    seasons = g._build_seasons(lc)
    teams = g._build_theme_teams(lc)
    return {
        "presets": presets,
        "slice_instances": instances,
        "slice_ais": slice_ais,
        "ai_profiles": g._build_ai_profiles(),
        "enemy_ais": g._build_enemy_ai(),
        "ai_modifiers": g._build_ai_modifiers(),
        "teams": teams,
        "seasons": seasons,
        "levels": levels,
    }


def _slot_alloc(level_id: int):
    counter = {"v": 90000 + level_id * 10}
    def alloc():
        counter["v"] += 1
        return counter["v"]
    return alloc


def build_dataset(tag_rows: list[dict]) -> dict:
    """加载主生成器默认数据集,逐关 patch,返回带 9xxx 虚拟行的完整产物。"""
    ds = _build_default_dataset()
    levels_by_id = {r["ID"]: r for r in ds["levels"]}
    insts_by_id = {r["ID"]: r for r in ds["slice_instances"]}
    ais_by_sid = {r["SliceID"]: r for r in ds["slice_ais"]}
    library_snapshot = {"insts": insts_by_id, "ais": ais_by_sid}

    for trow in tag_rows:
        if not trow["Tags"]:
            continue
        lid = trow["ID"]
        level_row = levels_by_id[lid]
        sl_ids = _json.loads(level_row["SliceList"])
        slice_ai_view = [ais_by_sid[s] for s in sl_ids if s in ais_by_sid]
        slice_inst_view = [insts_by_id[s] for s in sl_ids if s in insts_by_id]

        ctx = level_tag_lib.PatchContext(
            level_row=level_row,
            slice_ai_rows=ds["slice_ais"],          # 直接给整张表(patch 内自行 append)
            slice_instance_rows=ds["slice_instances"],
            new_id_alloc=_slot_alloc(lid),
            level_in_round=trow["LevelInRound"],
            tier=trow["Tier"],
            library=library_snapshot,
        )
        for tag in trow["Tags"]:
            level_tag_lib.TAG_REGISTRY[tag].patch(ctx)

    return ds


def validate_dataset(ds: dict) -> None:
    """生成阶段校验(spec §7)。"""
    errors: list[str] = []
    inst_ids = {r["ID"] for r in ds["slice_instances"]}
    ai_sids = {r["SliceID"] for r in ds["slice_ais"]}

    for r in ds["levels"]:
        sl = _json.loads(r["SliceList"])
        n = len(sl)
        if not (0 < r["DrawThreshold"] < r["WinThreshold"] <= n):
            errors.append(
                f"level {r['ID']} 阈值非法: lose<draw<win<=n 不成立 "
                f"(draw={r['DrawThreshold']}, win={r['WinThreshold']}, n={n})"
            )
        for s in sl:
            if s not in inst_ids:
                errors.append(f"level {r['ID']} SliceList 含未注册 SliceInstance: {s}")
        if not (1001 <= r["AiProfileID"] <= 1010):
            errors.append(f"level {r['ID']} AiProfileID 越界: {r['AiProfileID']}")

    for r in ds["slice_ais"]:
        if r["SliceID"] not in inst_ids:
            errors.append(f"SliceAi {r['ID']} 引用未注册 SliceInstance: {r['SliceID']}")

    if errors:
        raise ValidationError(errors)
```

- [ ] **Step 4: 跑测试看绿**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_apply.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add output/test-config/level-tags/apply_level_tags.py output/test-config/level-tags/tests/test_apply.py
git commit -m "feat(level-tags): apply 编排层(默认数据集 + 逐关 patch + 生成阶段校验)"
```

---

## Task 9: 写产物 xlsx + summary.json + CLI 入口

**Files:**
- Modify: `output/test-config/level-tags/apply_level_tags.py`
- Modify: `output/test-config/level-tags/tests/test_apply.py`

输出 9 张表 + 摘要 + 文件被占用回退 `*.generated.xlsx`(对齐主生成器约定)。

- [ ] **Step 1: 写产物输出测试**

追加到 `tests/test_apply.py`:
```python
def test_write_outputs_xlsx_with_9_sheets(tmp_path):
    out = _make_minimal_xlsx(tmp_path)
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    td_tags = app.load_tag_def(out)
    app.validate_loaded(rows, td_tags=td_tags)
    ds = app.build_dataset(rows)
    app.validate_dataset(ds)
    target = tmp_path / "ActivitySoccer.LevelTagged.xlsx"
    summary_path = tmp_path / "level-tag-summary.json"
    app.write_outputs(ds, rows, target, summary_path)
    assert target.exists()
    assert summary_path.exists()

    from openpyxl import load_workbook
    wb = load_workbook(target)
    expected = {
        "ActvSoccerSeasonCfg", "ActvSoccerLevelCfg",
        "ActvSoccerSlicePresetCfg", "ActvSoccerSliceInstanceCfg",
        "ActvSoccerSliceAiCfg", "ActvSoccerAiProfileCfg",
        "ActvSoccerEnemyAiCfg", "ActvSoccerAiModifierCfg",
        "ActvSoccerTeamCfg",
    }
    assert expected.issubset(set(wb.sheetnames))


def test_summary_records_tag_hits(tmp_path):
    out = _make_minimal_xlsx(tmp_path, tag_overrides={
        100: "boss",
        200: "boss",
        300: "hard_plus",
    })
    import apply_level_tags as app
    importlib.reload(app)
    rows = app.load_level_tag_cfg(out)
    td_tags = app.load_tag_def(out)
    app.validate_loaded(rows, td_tags=td_tags)
    ds = app.build_dataset(rows)
    target = tmp_path / "out.xlsx"
    summary_path = tmp_path / "summary.json"
    app.write_outputs(ds, rows, target, summary_path)
    import json
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["tag_hits"]["boss"] == [100, 200]
    assert summary["tag_hits"]["hard_plus"] == [300]
    assert summary["levels_total"] == 500
    assert summary["levels_with_tags"] == 3


def test_main_cli_clean_run_returns_zero(tmp_path, monkeypatch):
    out = _make_minimal_xlsx(tmp_path)
    import apply_level_tags as app
    importlib.reload(app)
    target = tmp_path / "tagged.xlsx"
    summary_path = tmp_path / "summary.json"
    rc = app.main(["--input", str(out), "--output", str(target),
                   "--summary", str(summary_path)])
    assert rc == 0
    assert target.exists()


def test_main_cli_validation_error_returns_one(tmp_path):
    out = _make_minimal_xlsx(tmp_path, tag_overrides={1: "ghost_xyz"})
    import apply_level_tags as app
    importlib.reload(app)
    rc = app.main(["--input", str(out),
                   "--output", str(tmp_path / "x.xlsx"),
                   "--summary", str(tmp_path / "x.json")])
    assert rc == 1


def test_main_cli_missing_input_returns_two(tmp_path):
    import apply_level_tags as app
    importlib.reload(app)
    rc = app.main(["--input", str(tmp_path / "absent.xlsx"),
                   "--output", str(tmp_path / "x.xlsx"),
                   "--summary", str(tmp_path / "x.json")])
    assert rc == 2
```

- [ ] **Step 2: 跑测试看红**

Run: `cd output/test-config/level-tags && python -m pytest tests/test_apply.py -v -k "write_outputs or summary_records or main_cli"`
Expected: 5 FAIL on `write_outputs` / `main` 不存在

- [ ] **Step 3: 实现产物输出 + CLI**

追加到 `apply_level_tags.py` 末尾:
```python
from collections import defaultdict


_SHEET_SCHEMA: dict[str, list[tuple[str, str, str]]] = {
    "ActvSoccerSeasonCfg": [
        ("cs", "int", "ID"), ("c", "string", "LeagueNameLcKey"),
        ("cs", "int", "NextSeason"), ("cs", "int", "ContractOfferCount"),
        ("-", "string", "Remark"),
    ],
    "ActvSoccerLevelCfg": [
        ("cs", "int", "ID"), ("cs", "bool", "IsTutorial"),
        ("cs", "int[]", "SliceList"), ("cs", "int", "AiProfileID"),
        ("cs", "int", "WinThreshold"), ("cs", "int", "DrawThreshold"),
        ("cs", "int", "TicketCost"), ("cs", "int", "OpponentTeamID"),
        ("cs", "int", "OpponentTeamStar"), ("cs", "int", "SeasonID"),
        ("-", "string", "Remark"),
    ],
    "ActvSoccerSlicePresetCfg": [
        ("cs", "int", "ID"), ("cs", "string", "SliceType"),
        ("c", "string", "NameLcKey"), ("c", "string[]", "Tags"),
        ("c", "ext", "BallPos"), ("c", "ext", "BallVector"),
        ("c", "int", "BallOwner"), ("c", "ext[]", "PlayersInit"),
        ("c", "float", "CameraFov"), ("c", "ext", "TargetPoint"),
        ("cs", "float", "OperableAngle"), ("c", "float", "AngleSpanMin"),
        ("c", "float", "AngleSpanMax"), ("c", "float", "AngleMaxCenterShift"),
        ("c", "float", "AngleMargin"), ("cs", "ext", "TypePayload"),
        ("c", "string[]", "RecommendedModes"), ("-", "string", "Remark"),
    ],
    "ActvSoccerSliceInstanceCfg": [
        ("cs", "int", "ID"), ("cs", "string", "SliceType"),
        ("cs", "int", "PresetID"), ("c", "float", "OverrideOperableAngle"),
        ("cs", "string", "ObjectiveType"), ("cs", "ext[]", "ExtraObjectives"),
        ("cs", "ext[]", "Modifiers"), ("-", "string", "Remark"),
    ],
    "ActvSoccerSliceAiCfg": [
        ("cs", "int", "ID"), ("cs", "int", "SliceID"),
        ("cs", "int", "AiProfileID"), ("cs", "int", "GoalkeeperAiID"),
        ("cs", "int", "DefenderAiID"), ("cs", "int", "ShooterAiID"),
        ("cs", "int", "ModifierID"), ("cs", "bool", "IsGuideAi"),
        ("cs", "bool", "RewindRandom"), ("cs", "int", "OverrideReactionTimeMs"),
        ("-", "string", "Remark"),
    ],
    "ActvSoccerAiProfileCfg": [
        ("cs", "int", "ID"), ("cs", "string", "Difficulty"),
        ("cs", "int", "GoalkeeperSaveRate"), ("cs", "int", "DefenderSuccessRate"),
        ("cs", "int", "ShooterSuccessRate"), ("cs", "int", "DeadCornerCanSave"),
        ("cs", "int", "ReactionTimeMs"), ("-", "string", "Remark"),
    ],
    "ActvSoccerEnemyAiCfg": [
        ("cs", "int", "ID"), ("cs", "int", "Duty"),
        ("cs", "int", "SaveWeight"), ("cs", "int", "LeftWeight"),
        ("cs", "int", "RightWeight"), ("cs", "int", "UpWeight"),
        ("cs", "int", "InterceptWeight"), ("cs", "int", "ClearanceWeight"),
        ("cs", "int", "KeeperCatchFail"), ("cs", "int", "OutOfBoundsFail"),
        ("c", "string", "AnimationKey"), ("-", "string", "Remark"),
    ],
    "ActvSoccerAiModifierCfg": [
        ("cs", "int", "ID"), ("cs", "string", "ModifierType"),
        ("cs", "string", "Param1Key"), ("cs", "string", "Param1Value"),
        ("cs", "string", "Param2Key"), ("cs", "string", "Param2Value"),
        ("cs", "string", "Param3Key"), ("cs", "string", "Param3Value"),
        ("-", "string", "Remark"),
    ],
    "ActvSoccerTeamCfg": [
        ("cs", "int", "ID"), ("c", "string", "NameLcKey"),
        ("cs", "string", "Region"), ("c", "string", "KitKey"),
        ("c", "string", "BadgeKey"), ("-", "string", "Remark"),
    ],
}


def _write_sheet(wb, name: str, schema: list[tuple[str, str, str]], rows: list[dict]) -> None:
    ws = wb.create_sheet(name)
    for col_idx, (read, type_, field) in enumerate(schema, start=1):
        ws.cell(1, col_idx, read)
        ws.cell(2, col_idx, type_)
        ws.cell(3, col_idx, field)
    for r_idx, row in enumerate(rows, start=9):
        for c_idx, (_, type_, field) in enumerate(schema, start=1):
            val = row.get(field)
            if val is None:
                if type_ == "ext[]":
                    val = "[]"
                elif type_ == "ext":
                    val = "{}"
            if val is not None:
                ws.cell(r_idx, c_idx, val)


def write_outputs(ds: dict, tag_rows: list[dict], target: Path, summary_path: Path) -> Path:
    """写 9 表 xlsx + summary.json。文件被占用时回退 *.generated.xlsx。"""
    from openpyxl import Workbook
    target = Path(target); summary_path = Path(summary_path)

    wb = Workbook(); wb.remove(wb.active)
    _write_sheet(wb, "ActvSoccerSeasonCfg", _SHEET_SCHEMA["ActvSoccerSeasonCfg"], ds["seasons"])
    _write_sheet(wb, "ActvSoccerLevelCfg", _SHEET_SCHEMA["ActvSoccerLevelCfg"], ds["levels"])
    _write_sheet(wb, "ActvSoccerSlicePresetCfg", _SHEET_SCHEMA["ActvSoccerSlicePresetCfg"], ds["presets"])
    _write_sheet(wb, "ActvSoccerSliceInstanceCfg", _SHEET_SCHEMA["ActvSoccerSliceInstanceCfg"], ds["slice_instances"])
    _write_sheet(wb, "ActvSoccerSliceAiCfg", _SHEET_SCHEMA["ActvSoccerSliceAiCfg"], ds["slice_ais"])
    _write_sheet(wb, "ActvSoccerAiProfileCfg", _SHEET_SCHEMA["ActvSoccerAiProfileCfg"], ds["ai_profiles"])
    _write_sheet(wb, "ActvSoccerEnemyAiCfg", _SHEET_SCHEMA["ActvSoccerEnemyAiCfg"], ds["enemy_ais"])
    _write_sheet(wb, "ActvSoccerAiModifierCfg", _SHEET_SCHEMA["ActvSoccerAiModifierCfg"], ds["ai_modifiers"])
    _write_sheet(wb, "ActvSoccerTeamCfg", _SHEET_SCHEMA["ActvSoccerTeamCfg"], ds["teams"])

    actual = target
    try:
        wb.save(actual)
    except PermissionError:
        actual = target.with_suffix(".generated.xlsx")
        wb.save(actual)
        print(f"[warn] {target} 被占用,回退写入 {actual}")

    # summary.json
    tag_hits: dict[str, list[int]] = defaultdict(list)
    levels_with_tags = 0
    for trow in tag_rows:
        if trow["Tags"]:
            levels_with_tags += 1
            for tag in trow["Tags"]:
                tag_hits[tag].append(trow["ID"])
    summary = {
        "input": str(target),
        "levels_total": len(ds["levels"]),
        "levels_with_tags": levels_with_tags,
        "virtual_slice_instance_count": sum(1 for r in ds["slice_instances"] if r["ID"] >= 90000),
        "virtual_slice_ai_count": sum(1 for r in ds["slice_ais"] if r["ID"] >= 90000),
        "tag_hits": {k: sorted(v) for k, v in sorted(tag_hits.items())},
    }
    summary_path.write_text(_json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return actual


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=HERE / "ActivitySoccer.LevelTagged.xlsx")
    parser.add_argument("--summary", type=Path, default=HERE / "level-tag-summary.json")
    args = parser.parse_args(argv)

    try:
        rows = load_level_tag_cfg(args.input)
        td_tags = load_tag_def(args.input)
    except FileNotFoundError as e:
        print(f"[error] 输入文件不存在: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"[error] 输入加载失败: {e}", file=sys.stderr)
        return 2

    try:
        validate_loaded(rows, td_tags=td_tags)
    except ValidationError as e:
        print("[error] 加载阶段校验失败:", file=sys.stderr)
        for err in e.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    ds = build_dataset(rows)
    try:
        validate_dataset(ds)
    except ValidationError as e:
        print("[error] 生成阶段校验失败:", file=sys.stderr)
        for err in e.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    actual = write_outputs(ds, rows, args.output, args.summary)
    tagged = sum(1 for r in rows if r["Tags"])
    print(f"[ok] 关卡 tag 产物写入: {actual} (贴 tag 关数 {tagged}/500)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 跑测试看绿**

Run: `cd output/test-config/level-tags && python -m pytest tests/ -v`
Expected: 全套测试 passed(level_tag_lib 19 + template 4 + apply 16)

- [ ] **Step 5: 端到端冒烟 —— 用空模板真跑一次**

Run:
```bash
python3 output/test-config/level-tags/apply_level_tags.py
```

Expected stdout:
```
[ok] 关卡 tag 产物写入: .../ActivitySoccer.LevelTagged.xlsx (贴 tag 关数 0/500)
```

- [ ] **Step 6: Commit**

```bash
git add output/test-config/level-tags/apply_level_tags.py output/test-config/level-tags/tests/test_apply.py
git commit -m "feat(level-tags): 9 表 xlsx 输出 + summary.json + main CLI(退出码 0/1/2)"
```

---

## Task 10: 集成验证 + 文档指针

**Files:**
- Modify: `output/test-config/level-tags/LevelTagCfg.xlsx`(贴 5 个样例 tag 验证)
- Modify: `output/2026世界杯主题活动-配置表结构.md`(底部加一节指针)
- Modify: `output/test-config/test-config-summary.json`(可选,记录工具产物路径)

- [ ] **Step 1: 在 LevelTagCfg.xlsx 贴 5 个样例 tag 验证全链路**

打开 `output/test-config/level-tags/LevelTagCfg.xlsx`(或脚本贴),分别在以下关 Tags 列写入:
- level 100: `boss`(只改 LevelCfg)
- level 200: `set_piece, hard_plus`(slice + ai 复合)
- level 250: `extreme_keeper`(触发 9xxx 虚拟行)
- level 300: `must_win`(纯阈值)
- level 400: `tutorial`(覆盖 SliceList,验证不冲突)

可用脚本一次贴上(便于复现):
```bash
cd output/test-config/level-tags && python -c "
from openpyxl import load_workbook
wb = load_workbook('LevelTagCfg.xlsx')
ws = wb['LevelTags']
samples = {100: 'boss', 200: 'set_piece, hard_plus', 250: 'extreme_keeper', 300: 'must_win', 400: 'tutorial'}
for lid, tags in samples.items():
    ws.cell(9 + lid - 1, 5, tags)
wb.save('LevelTagCfg.xlsx')
print('samples written')
"
```

- [ ] **Step 2: 跑工具,期望 0 退出**

Run:
```bash
python3 output/test-config/level-tags/apply_level_tags.py
```

Expected:
```
[ok] 关卡 tag 产物写入: .../ActivitySoccer.LevelTagged.xlsx (贴 tag 关数 5/500)
```

- [ ] **Step 3: 验 summary.json 含命中**

Run:
```bash
cd output/test-config/level-tags && python -c "
import json
s = json.load(open('level-tag-summary.json', encoding='utf-8'))
assert s['levels_with_tags'] == 5
assert s['tag_hits']['boss'] == [100]
assert s['tag_hits']['extreme_keeper'] == [250]
assert s['virtual_slice_instance_count'] >= 1
print('summary ok:', s['tag_hits'])
"
```

Expected: `summary ok: {'boss': [100], 'extreme_keeper': [250], 'hard_plus': [200], 'must_win': [300], 'set_piece': [200], 'tutorial': [400]}`

- [ ] **Step 4: 在配置表结构文档底部加指针**

`output/2026世界杯主题活动-配置表结构.md` 底部「测试配置与正式表」节追加一行:

```markdown
- 关卡 tag 工具:`output/test-config/level-tags/`(spec `docs/superpowers/specs/2026-06-17-worldcup-level-config-tool-design.md`,产物 `ActivitySoccer.LevelTagged.xlsx`,与主 ActivitySoccer.xlsx 之间的合并由 config-table-editor 负责)
```

- [ ] **Step 5: Commit 样例 tag + 文档指针**

```bash
git add output/test-config/level-tags/LevelTagCfg.xlsx output/2026世界杯主题活动-配置表结构.md
git commit -m "feat(level-tags): 5 个样例 tag 端到端验证 + 配置表结构文档指针"
```

- [ ] **Step 6: 最终自检清单**

人工跑一遍(对照 spec §10 验收清单):
- [ ] 不传 LevelTagCfg.xlsx 时报错,退出码 2
- [ ] 全空 Tags 表跑通后产物 = 主生成器关卡产物族 9 表(逐字段 diff)
- [ ] 互斥组 tag 同行存在时报错,退出码 1
- [ ] 未注册 tag 时报错,退出码 1
- [ ] 5 个样例 tag 在样例关上 patch 后产物可读、引用完整,退出码 0
- [ ] summary.json 含每个 tag 的命中关 ID 列表

全部 ✓ 后,本计划完成。

---

## 验证全链路最终状态

最终目录:
```
output/test-config/level-tags/
├── __init__.py
├── level_tag_lib.py                # 16 tag 注册器 + patch 函数
├── apply_level_tags.py             # 入口:加载/校验/patch/写产物
├── generate_level_tag_template.py  # 模板生成器
├── LevelTagCfg.xlsx                # 策划填表入口(git 跟踪)
├── ActivitySoccer.LevelTagged.xlsx # 产物(.gitignore)
├── level-tag-summary.json          # 摘要(.gitignore)
└── tests/
    ├── __init__.py
    ├── test_level_tag_lib.py       # 19 tests
    ├── test_template.py            # 4 tests
    └── test_apply.py               # 16 tests
```

预期全套测试:`pytest output/test-config/level-tags/tests/ -v` → 39 passed。
