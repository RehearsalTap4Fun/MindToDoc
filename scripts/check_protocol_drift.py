#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协议 ↔ 代码常量段 drift 检查(spec §6.2)。

用法:
    python scripts/check_protocol_drift.py
    python scripts/check_protocol_drift.py --protocol references/soccer-coordinate-protocol.md \
                                           --gen output/test-config/generate_activity_soccer_test_config.py

行为:
1. 解析协议 §3-§4 的 markdown 表格,抓「字段 = 值」(支持 m / mm / 度等单位标注)。
2. 解析主生成器顶部「# === 坐标系协议 v1 ===」到下一个 # === 之间的 Python 顶层赋值。
3. 按硬编码映射表逐条对照。不一致即收集错误并非零退出。
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

# 协议字段名 → 代码常量名(子串匹配 / 提取数值)
PROTOCOL_TO_CONST: dict[str, str] = {
    "球门宽度": "GOAL_WIDTH",
    "球门高度": "GOAL_HEIGHT",
    "死角厚度": "DEAD_CORNER_THICKNESS",
    "球员碰撞半径": "PLAYER_RADIUS",
    "球碰撞半径": "BALL_RADIUS",
    "球员可控球距离": "BALL_CONTROL_DISTANCE",
    "中圈半径": "CENTER_CIRCLE_RADIUS",
}


def parse_protocol_constants(path: Path) -> dict[str, float]:
    """从协议 markdown 抓「| 字段 | 数值 | 单位 |」三列。"""
    out: dict[str, float] = {}
    pattern = re.compile(r"^\|\s*([^\|]+?)\s*\|\s*([0-9.+\-]+)\s*\|\s*[^\|]+\|")
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = pattern.match(line)
        if m:
            field = m.group(1).strip()
            try:
                out[field] = float(m.group(2))
            except ValueError:
                pass
    return out


def parse_code_constants(path: Path) -> dict[str, float]:
    """从主生成器顶部常量段抓 NAME = literal 顶层赋值。"""
    text = path.read_text(encoding="utf-8")
    start = text.find("# === 坐标系协议 v1 ===")
    if start < 0:
        return {}
    rest = text[start:]
    end_match = re.search(r"\n# ===", rest[len("# === 坐标系协议 v1 ==="):])
    if end_match:
        rest = rest[: len("# === 坐标系协议 v1 ===") + end_match.start()]
    out: dict[str, float] = {}
    try:
        tree = ast.parse(rest)
    except SyntaxError:
        return out
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name):
                val = _literal_to_float(node.value)
                if val is not None:
                    out[tgt.id] = val
    return out


def _literal_to_float(node) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _literal_to_float(node.operand)
        return -v if v is not None else None
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path,
                        default=Path("references/soccer-coordinate-protocol.md"))
    parser.add_argument("--gen", type=Path,
                        default=Path("output/test-config/generate_activity_soccer_test_config.py"))
    args = parser.parse_args(argv)

    if not args.protocol.exists():
        print(f"[error] 协议文件不存在: {args.protocol}", file=sys.stderr)
        return 2
    if not args.gen.exists():
        print(f"[error] 主生成器不存在: {args.gen}", file=sys.stderr)
        return 2

    protocol_vals = parse_protocol_constants(args.protocol)
    code_vals = parse_code_constants(args.gen)

    errors: list[str] = []
    for prot_key, code_key in PROTOCOL_TO_CONST.items():
        prot_val = protocol_vals.get(prot_key)
        code_val = code_vals.get(code_key)
        if prot_val is None:
            errors.append(f"协议未找到字段: '{prot_key}'")
            continue
        if code_val is None:
            errors.append(f"代码常量段未定义: {code_key}(协议 '{prot_key}' = {prot_val})")
            continue
        if abs(prot_val - code_val) > 1e-6:
            errors.append(f"drift: 协议 '{prot_key}' = {prot_val} != 代码 {code_key} = {code_val}")

    if errors:
        print(f"[FAIL] {len(errors)} 处 drift:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"[ok] 协议 ↔ 代码常量段一致({len(PROTOCOL_TO_CONST)} 项)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
