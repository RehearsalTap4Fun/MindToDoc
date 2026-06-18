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


import json
import math


def _slice_count_of(level_row: dict) -> int:
    return len(json.loads(level_row["SliceList"]))


# --- patch 函数设计约定 ---
# 1. 阈值类 patch (boss/must_win/lenient) 不做 n<2 防御:
#    - 主生成器 _slice_count 最小返回 2,n=1 在生产路径不可达
#    - lenient 与 must_win 同 mutex_group="threshold" 不叠加
#    - 校验由 apply_level_tags.validate_dataset 在 generation 阶段统一抓
#    详见 spec §4.4 (校验阶段) 与 §7 (validate 项)
# 2. patch 直接修改 ctx.level_row,不返回值


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


def _slice_id(tier: int, stype: int, variant: int) -> int:
    return tier * 100 + stype * 10 + variant


def _slice_type(sid: int) -> int:
    return (sid // 10) % 10


def _patch_set_piece(ctx: PatchContext) -> None:
    sl = json.loads(ctx.level_row["SliceList"])
    has_fk = any(_slice_type(s) == 2 for s in sl)
    has_pk = any(_slice_type(s) == 3 for s in sl)
    if not has_fk:
        sl.insert(0, _slice_id(ctx.tier, 2, 1))
    if not has_pk:
        sl.insert(1 if not has_fk else 0, _slice_id(ctx.tier, 3, 1))
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

