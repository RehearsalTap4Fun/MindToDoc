#!/usr/bin/env python3
"""Validate audio production artifacts by content and workflow stage."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from audio_sheet_workbook import read_workbook
from workspace_paths import find_workspace_root, production_root


REQUIRED_FILES = [
    "audio_demand.xlsx", "audio_demand_master.csv", "audio_sheet_rows.json",
    "planner_demand_review.md", "planner_demand_review.json", "planner_demand_review.xlsx",
    "sheet.meta.json", "summary.md", "sound_design.json",
    "company_library_search_plan.csv", "company_library_search_results.json",
    "company_library_candidates.csv", "company_library_previews",
    "company_library_review.html",
    "company_library_review_manifest.json", "company_library_preview_map.json",
    "planner_feedback.csv", "audio_preference_profiles.json",
    "ai_gap_queue.csv", "ai_candidate_manifest.json", "planner_decisions.json",
    "decision_application_manifest.json", "final_package_manifest.json", "wav",
]
BASE_COLUMNS = ["事件名", "音效资源名", "功能模块", "声音类型", "描述", "触发时机", "生产状态"]
VALID_TAGS = {"新增", "复用", "沿用X1"}
VERIFIED_REUSE_STATUSES = {"reuse_verified", "reuse_generated_in_current_sheet", "selected_company_library", "selected_ai", "generated"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_artifact_path(workspace: Path, prod: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    prod_relative = prod / value
    if prod_relative.exists():
        return prod_relative
    return workspace / value


def check_prepared(workspace: Path, prod: Path, sheet_name: str, errors: list[str], warnings: list[str]) -> dict[str, Any]:
    for name in REQUIRED_FILES:
        if not (prod / name).exists():
            errors.append(f"missing required artifact: {name}")

    workbook = workspace / ".gdconfig_tmp/output/audio/audio_sheet.xlsx"
    sheets = read_workbook(workbook)
    rows = sheets.get(sheet_name, [])
    if not rows:
        errors.append(f"audio_sheet missing or empty sheet: {sheet_name}")
        return {}
    headers = rows[0]
    for column in BASE_COLUMNS:
        if column not in headers:
            errors.append(f"audio_sheet missing column: {column}")
    indexes = {name: index for index, name in enumerate(headers)}
    events: set[str] = set()
    assets: dict[str, str] = {}
    reuse_unverified: list[str] = []
    for number, values in enumerate(rows[1:], 2):
        if not any(values):
            continue
        def value(name: str) -> str:
            index = indexes.get(name, -1)
            return values[index].strip() if 0 <= index < len(values) else ""
        event = value("事件名")
        asset = value("音效资源名")
        tag = value("生产状态")
        resource_status = value("资源状态")
        if not all(value(column) for column in BASE_COLUMNS):
            errors.append(f"audio_sheet row {number} has empty required values")
        if event in events:
            errors.append(f"duplicated event: {event}")
        events.add(event)
        if tag not in VALID_TAGS:
            errors.append(f"invalid production tag at row {number}: {tag}")
        if tag == "新增":
            assets[asset] = "新增"
        else:
            assets.setdefault(asset, tag)
            if resource_status not in VERIFIED_REUSE_STATUSES:
                reuse_unverified.append(f"{event}->{asset}({resource_status or 'empty'})")

    plan = read_csv(prod / "company_library_search_plan.csv") if (prod / "company_library_search_plan.csv").exists() else []
    planned_assets = {row.get("asset_name", "") for row in plan if row.get("library_query", "").strip()}
    missing_plans = sorted(asset for asset, tag in assets.items() if tag == "新增" and asset not in planned_assets)
    if missing_plans:
        errors.append(f"new assets missing company search queries: {', '.join(missing_plans)}")
    blocking_reuse = [
        item for item in reuse_unverified
        if assets.get(item.split("->", 1)[1].split("(", 1)[0]) != "新增"
    ]
    if blocking_reuse:
        errors.append(
            "reuse assets are not verified; do not simulate reuse. "
            "Mark them as 新增 if they must be produced this round: "
            + ", ".join(blocking_reuse[:20])
        )

    ai_rows = read_csv(prod / "ai_gap_queue.csv") if (prod / "ai_gap_queue.csv").exists() else []
    valid_ai_statuses = {
        "blocked_pending_company_library_review", "approved_for_ai", "planned",
        "generated", "selected_company_library", "selected_ai", "rejected",
    }
    invalid_ai = [row.get("音效资源名", "") for row in ai_rows if row.get("status") not in valid_ai_statuses]
    if invalid_ai:
        errors.append(f"AI queue has invalid statuses: {', '.join(invalid_ai)}")
    if any(row.get("status") == "approved_for_ai" for row in ai_rows):
        warnings.append("AI queue contains approved rows; verify planner decisions before generation")

    review_path = prod / "planner_demand_review.json"
    if review_path.exists():
        review = load_json(review_path)
        status = str(review.get("status") or "").strip()
        if status not in {"pending_planner_review", "approved"}:
            errors.append(f"invalid planner demand review status: {status}")
        if status != "approved":
            warnings.append("planner demand review is pending; do not run company search or AI generation")

    return {"events": events, "assets": assets, "rows": rows}


def check_review_ready(workspace: Path, prod: Path, prepared: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    manifest_path = prod / "company_library_review_manifest.json"
    if not manifest_path.exists():
        return
    manifest = load_json(manifest_path)
    events = manifest if isinstance(manifest, list) else manifest.get("events", [])
    by_asset: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        by_asset.setdefault(str(event.get("asset_name") or event.get("assetName") or ""), []).extend(event.get("candidates", []))
    candidate_rows = read_csv(prod / "company_library_candidates.csv") if (prod / "company_library_candidates.csv").exists() else []
    explicit_no_candidates = {
        row.get("asset_name", "")
        for row in candidate_rows
        if not row.get("candidate_id", "").strip()
        and row.get("search_status") == "ok"
        and row.get("planner_decision") == "no_company_candidate"
    }
    assets = prepared.get("assets", {})
    for asset, tag in assets.items():
        if tag != "新增":
            continue
        candidates = by_asset.get(asset, [])
        if not candidates and asset not in explicit_no_candidates:
            errors.append(f"new asset has no company candidates: {asset}")
    ai_manifest = load_json(prod / "ai_candidate_manifest.json") if (prod / "ai_candidate_manifest.json").exists() else {}
    ai_rows = ai_manifest.get("candidates", []) if isinstance(ai_manifest, dict) else []
    ai_by_asset: dict[str, list[dict[str, Any]]] = {}
    for candidate in ai_rows:
        ai_by_asset.setdefault(str(candidate.get("assetName") or candidate.get("asset_name") or ""), []).append(candidate)
    decision_path = prod / "planner_decisions.json"
    decision_rows = []
    if decision_path.exists():
        decisions = load_json(decision_path)
        decision_rows = decisions.get("decisions", []) if isinstance(decisions, dict) else decisions
    selected_assets = {
        str(row.get("asset_name") or row.get("assetName") or "")
        for row in decision_rows
        if (row.get("event_decision") or row.get("decision")) in {"direct_use", "modify_use"}
    }
    for event in events:
        asset = str(event.get("asset_name") or event.get("assetName") or "")
        if not asset or assets.get(asset) != "新增":
            continue
        if (event.get("qualified_candidate_count") or 0) > 0:
            continue
        if asset in selected_assets:
            continue
        generated = [candidate for candidate in ai_by_asset.get(asset, []) if candidate.get("status") == "generated"]
        if len(generated) < 3:
            errors.append(f"low-score company gap needs at least 3 generated AI candidates: {asset}")
            continue
        for candidate in generated:
            path = str(candidate.get("wavPath") or candidate.get("output_path") or "")
            target = resolve_artifact_path(workspace, prod, path) if path else Path()
            if not path or not target.exists():
                errors.append(f"AI candidate audio missing: {asset} -> {path}")
    preview_map = load_json(prod / "company_library_preview_map.json") if (prod / "company_library_preview_map.json").exists() else {}
    playable = sum(1 for item in preview_map.values() if item.get("status") == "downloaded") if isinstance(preview_map, dict) else 0
    if playable == 0:
        errors.append("review page has no downloaded playable candidates")
    html = (prod / "company_library_review.html").read_text(encoding="utf-8") if (prod / "company_library_review.html").exists() else ""
    for snippet in ('id="scoreFilter"', 'id="candidateSort"', "直接用", "改后用", "不合适"):
        if snippet not in html:
            errors.append(f"review page missing required UI: {snippet}")


def check_handoff_ready(workspace: Path, prod: Path, prepared: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    decisions = load_json(prod / "planner_decisions.json") if (prod / "planner_decisions.json").exists() else {}
    rows = decisions.get("decisions", []) if isinstance(decisions, dict) else decisions
    decided_assets = {
        str(row.get("asset_name") or row.get("assetName") or "")
        for row in rows
        if row.get("demand_tag") == "新增"
        and (row.get("event_decision") or row.get("decision"))
    }
    for asset, tag in prepared.get("assets", {}).items():
        target = workspace / "audio" / f"{asset}.ogg"
        if tag == "新增" and asset not in decided_assets:
            errors.append(f"new asset has no planner decision: {asset}")
        if not target.exists():
            errors.append(f"final OGG missing: {target}")
        elif target.stat().st_size < 64 or target.read_bytes()[:4] != b"OggS":
            errors.append(f"final OGG is invalid or empty: {target}")
    pending_ai = [row for row in read_csv(prod / "ai_gap_queue.csv") if row.get("status") in {"blocked_pending_company_library_review", "approved_for_ai", "planned"}]
    if pending_ai:
        errors.append(f"AI queue still has {len(pending_ai)} unresolved rows")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-name", required=True)
    parser.add_argument("--stage", choices=["prepared", "review-ready", "handoff-ready"], default="prepared")
    parser.add_argument("--workspace-root", type=Path)
    args = parser.parse_args()
    workspace = args.workspace_root.resolve() if args.workspace_root else find_workspace_root()
    prod = production_root(workspace, args.sheet_name)
    errors: list[str] = []
    warnings: list[str] = []
    prepared = check_prepared(workspace, prod, args.sheet_name, errors, warnings)
    if args.stage in {"review-ready", "handoff-ready"}:
        check_review_ready(workspace, prod, prepared, errors, warnings)
    if args.stage == "handoff-ready":
        check_handoff_ready(workspace, prod, prepared, errors, warnings)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print(f"validation stage={args.stage} errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
