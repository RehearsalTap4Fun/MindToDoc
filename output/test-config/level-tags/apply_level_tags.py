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
