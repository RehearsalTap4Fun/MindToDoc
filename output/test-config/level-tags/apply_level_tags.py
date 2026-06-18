# -*- coding: utf-8 -*-
"""关卡 tag 配置工具入口(加载 + 校验阶段)。

后续 Task 8 在本文件追加 patch 编排,Task 9 追加 xlsx 写出。
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

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

    lib_tags = set(level_tag_lib.TAG_REGISTRY.keys())
    if td_tags != lib_tags:
        only_def = td_tags - lib_tags
        only_lib = lib_tags - td_tags
        if only_def:
            errors.append(f"TagDef 多余 tag(lib 未注册): {sorted(only_def)}")
        if only_lib:
            errors.append(f"lib 注册但 TagDef 缺少: {sorted(only_lib)}")

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


import json as _json


def _import_main_generator():
    """惰性导入主生成器,避免顶层 import 顺序污染。"""
    sys.path.insert(0, str(HERE.parent))
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
        ctx = level_tag_lib.PatchContext(
            level_row=level_row,
            slice_ai_rows=ds["slice_ais"],
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
