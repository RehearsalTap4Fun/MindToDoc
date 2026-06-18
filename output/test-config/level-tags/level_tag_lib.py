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

