#!/usr/bin/env python3
"""Apply exported planner decisions to AI gaps and final production WAV files."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from workspace_paths import find_workspace_root, production_root


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def resolve_source(workspace: Path, prod: Path, value: str) -> Path | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return None
    path = Path(parsed.path if parsed.scheme == "file" else value)
    if path.is_absolute() and path.exists():
        return path
    relative = str(path).lstrip("/")
    for root in (prod, workspace):
        candidate = root / relative
        if candidate.exists():
            return candidate
    return None


def copy_as_wav(source: Path, target: Path, ffmpeg: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".wav":
        shutil.copy2(source, target)
        return
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-vn", "-acodec", "pcm_s16le", str(target),
    ], check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-name", required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    workspace = args.workspace_root.resolve() if args.workspace_root else find_workspace_root()
    prod = production_root(workspace, args.sheet_name)
    raw = json.loads(args.decisions.read_text(encoding="utf-8-sig"))
    decisions = raw.get("decisions", []) if isinstance(raw, dict) else raw
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("planner decisions must contain a non-empty array")

    queue_path = prod / "ai_gap_queue.csv"
    queue_rows = read_csv(queue_path)
    queue_fields = list(queue_rows[0].keys()) if queue_rows else ["音效资源名", "prompt", "avoid", "duration", "status", "priority"]
    queue_by_asset = {row.get("音效资源名", ""): row for row in queue_rows}
    applied: list[dict[str, str]] = []

    for row in decisions:
        asset = str(row.get("asset_name") or row.get("assetName") or "").strip()
        event = str(row.get("event_name") or row.get("eventName") or "").strip()
        decision = str(row.get("event_decision") or row.get("decision") or "").strip()
        demand_tag = str(row.get("demand_tag") or "").strip()
        if not asset or not event:
            raise ValueError("each planner decision requires event_name and asset_name")
        if demand_tag in {"复用", "沿用X1"}:
            applied.append({"event": event, "asset": asset, "result": "reuse_existing"})
            continue
        if decision in {"ai_needed", "auto_ai"}:
            if asset not in queue_by_asset:
                raise ValueError(f"AI decision has no queue row: {asset}")
            queue_by_asset[asset]["status"] = "approved_for_ai"
            applied.append({"event": event, "asset": asset, "result": "approved_for_ai"})
            continue
        if decision not in {"direct_use", "modify_use"}:
            applied.append({"event": event, "asset": asset, "result": decision or "undecided"})
            continue
        source_value = str(
            row.get("selected_source_path")
            or row.get("selected_local_preview_url")
            or row.get("source_path")
            or ""
        )
        source = resolve_source(workspace, prod, source_value)
        if source is None:
            raise FileNotFoundError(f"selected local candidate not found for {event}: {source_value}")
        target = prod / "wav" / f"{asset}.wav"
        copy_as_wav(source, target, args.ffmpeg)
        if asset in queue_by_asset:
            selected_id = str(row.get("selected_candidate_id") or "")
            queue_by_asset[asset]["status"] = "selected_ai" if selected_id.startswith("ai:") else "selected_company_library"
        applied.append({"event": event, "asset": asset, "result": decision, "wav": str(target.relative_to(workspace))})

    write_csv(queue_path, queue_rows, queue_fields)
    (prod / "planner_decisions.json").write_text(json.dumps({"decisions": decisions}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (prod / "decision_application_manifest.json").write_text(json.dumps({
        "sheetName": args.sheet_name, "applied": applied,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"applied planner decisions: {len(applied)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
