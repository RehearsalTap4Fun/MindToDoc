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
