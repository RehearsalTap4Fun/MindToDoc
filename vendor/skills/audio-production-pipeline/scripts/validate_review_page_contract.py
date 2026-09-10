#!/usr/bin/env python3
"""Validate that a generated planner review page follows the X15 page contract."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


CONTRACT_VERSION = "x15-planner-review-v1"


REQUIRED_SNIPPETS = [
    ("contract meta", f'name="x15-review-page-contract" content="{CONTRACT_VERSION}"'),
    ("contract body", f'data-review-page-contract="{CONTRACT_VERSION}"'),
    ("event list pane", 'id="eventList"'),
    ("detail pane", 'id="detail"'),
    ("in-page audio", "<audio controls"),
    ("decision direct use", "直接用"),
    ("decision modify use", "改后用"),
    ("decision reject", "不合适"),
    ("score filter", 'id="scoreFilter"'),
    ("score filter default", "中高分+最佳短"),
    ("score filter 60", "只看60分以上"),
    ("score filter all", "显示全部分数"),
    ("candidate sort", 'id="candidateSort"'),
    ("sort short first", "短候选优先"),
    ("sort score first", "匹配分优先"),
    ("sort rank first", "搜索排名优先"),
    ("candidate filter", 'id="candidateFilter"'),
    ("filter qualified", "有合格候选"),
    ("filter short", "有短候选"),
    ("filter triage", "需重点听"),
    ("filter no candidate", "无候选"),
    ("reuse filter", 'id="reuseFilter"'),
    ("reuse hidden default", "隐藏复用项"),
    ("reuse only", "只看复用项"),
    ("AI generate control", "AI生成候选"),
    ("combined opt-in", 'id="generateCombined"'),
    ("export decisions", 'id="exportBtn"'),
    ("one-click production handoff", 'id="submitPackageBtn"'),
    ("export feedback", 'id="exportFeedbackBtn"'),
    ("export AI queue", 'id="exportAiBtn"'),
    ("planner decisions filename", "x15_company_library_planner_decisions.json"),
    ("localStorage origin warning behavior", "installStateMigrationGuard"),
]


FORBIDDEN_PATTERNS = [
    ("external-only listening copy", re.compile(r"在线试听")),
    ("default checked combined", re.compile(r'id="generateCombined"[^>]*checked')),
]


def validate(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    for label, snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            errors.append(f"missing {label}: {snippet}")

    for label, pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            errors.append(f"forbidden {label}: {pattern.pattern}")

    if text.count("<audio controls") == 0:
        errors.append("no in-page audio controls found")

    if "复用项不生成AI" not in text:
        warnings.append("reuse rows may not be protected from AI generation")

    if "bestShortCandidate" not in text:
        warnings.append("best short candidate behavior not found")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path, help="Generated review HTML page")
    args = parser.parse_args()

    errors, warnings = validate(args.html)
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    if errors:
        print("Contract validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"OK: {args.html} follows {CONTRACT_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
