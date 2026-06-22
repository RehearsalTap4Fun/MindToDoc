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
    library: dict                        # reserved:只读快照,留给未来需要查库的 patch 使用;当前 16 个 patch 都不消费


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


def _patch_tutorial(ctx: PatchContext) -> None:
    ctx.level_row["IsTutorial"] = 1
    ctx.level_row["TicketCost"] = 0
    ctx.level_row["SliceList"] = "[201,202,203]"
    ctx.level_row["AiProfileID"] = 1001


def _register_level_only_tags() -> None:
    """注册不依赖 SliceAi/SliceInstance 的 4 个 level-only tag。
    幂等:重复调用先清同名条目再注册。"""
    for name in ("boss", "must_win", "lenient", "free_run", "tutorial"):
        TAG_REGISTRY.pop(name, None)
    register(TagSpec("boss", ("level",), None,
                     "对手 5 星 + 全胜阈值", _patch_boss))
    register(TagSpec("must_win", ("level",), "threshold",
                     "切片全胜才能赢", _patch_must_win))
    register(TagSpec("lenient", ("level",), "threshold",
                     "胜阈值降至 40%", _patch_lenient))
    register(TagSpec("tutorial", ("level", "slice"), "tutorial",
                     "强制引导关 + [201,202,203]", _patch_tutorial))


_register_level_only_tags()


def _slice_id(tier: int, stype: int, variant: int) -> int:
    return tier * 100 + stype * 10 + variant


def _slice_type(sid: int) -> int:
    return (sid // 10) % 10


def _patch_set_piece(ctx: PatchContext) -> None:
    sl = json.loads(ctx.level_row["SliceList"])
    additions: list[int] = []
    if not any(_slice_type(s) == 2 for s in sl):
        additions.append(_slice_id(ctx.tier, 2, 1))
    if not any(_slice_type(s) == 3 for s in sl):
        additions.append(_slice_id(ctx.tier, 3, 1))
    sl = sl + additions
    while len(sl) > 5:
        for idx in range(len(sl) - len(additions) - 1, -1, -1):
            if _slice_type(sl[idx]) not in (2, 3):
                del sl[idx]
                break
        else:
            del sl[-len(additions) - 1 if additions else -1]
    ctx.level_row["SliceList"] = json.dumps(sl)


def _patch_penalty_focus(ctx: PatchContext) -> None:
    sl = json.loads(ctx.level_row["SliceList"])
    if not any(_slice_type(s) == 3 for s in sl):
        sl.append(_slice_id(ctx.tier, 3, 1))
    while len(sl) > 5:
        for idx in range(len(sl) - 2, -1, -1):
            if _slice_type(sl[idx]) != 3:
                del sl[idx]
                break
        else:
            del sl[-2]
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
    for name in ("set_piece", "penalty_focus", "corner_focus", "gk_test",
                 "long_match", "short_match", "all_v2"):
        TAG_REGISTRY.pop(name, None)
    register(TagSpec("set_piece", ("slice",), None,
                     "保证至少 1 free_kick + 1 penalty", _patch_set_piece))
    register(TagSpec("penalty_focus", ("slice",), None,
                     "保证至少 1 penalty 切片", _patch_penalty_focus))
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
