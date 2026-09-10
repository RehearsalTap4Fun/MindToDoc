#!/usr/bin/env python3
"""Generate company-API AI candidates only for planner-approved gap rows."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from company_audio_api import DEFAULT_BASE_URL, generate_sound, load_token, missing_token_message
from workspace_paths import find_workspace_root, production_root


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-name", required=True)
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--queue", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--variants", type=int, default=3)
    parser.add_argument("--review-manifest", type=Path)
    parser.add_argument("--auto-approve-low-score", action="store_true")
    parser.add_argument("--duration", type=float, default=0)
    parser.add_argument("--prompt-influence", type=float, default=0.3)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.variants < 1:
        raise ValueError("variants must be at least 1")

    workspace = args.workspace_root.resolve() if args.workspace_root else find_workspace_root()
    prod = production_root(workspace, args.sheet_name)
    queue_path = args.queue.resolve() if args.queue else prod / "ai_gap_queue.csv"
    manifest_path = args.manifest.resolve() if args.manifest else prod / "ai_candidate_manifest.json"
    rows = read_csv(queue_path)
    fields = list(rows[0].keys()) if rows else ["音效资源名", "prompt", "avoid", "duration", "status", "priority"]
    if args.auto_approve_low_score:
        if not args.review_manifest or not args.review_manifest.exists():
            raise FileNotFoundError("--auto-approve-low-score requires --review-manifest")
        review = json.loads(args.review_manifest.read_text(encoding="utf-8-sig"))
        events = review if isinstance(review, list) else review.get("events", [])
        unresolved_assets = {
            str(event.get("asset_name") or event.get("assetName") or "")
            for event in events
            if event.get("demand_tag") not in {"复用", "沿用X1"}
            and ((event.get("candidate_count") or 0) <= 0 or (event.get("qualified_candidate_count") or 0) <= 0)
        }
        for row in rows:
            if row.get("音效资源名") in unresolved_assets and row.get("status") == "blocked_pending_company_library_review":
                row["status"] = "approved_for_ai"
        if not args.dry_run:
            write_csv(queue_path, rows, fields)
    approved = [row for row in rows if row.get("status") == "approved_for_ai"]
    if not approved:
        print("no approved_for_ai rows; nothing generated")
        return 0
    if not args.dry_run and shutil.which(args.ffmpeg) is None:
        raise FileNotFoundError(f"ffmpeg not found: {args.ffmpeg}")
    token = "" if args.dry_run else load_token(args.config_dir)
    if not args.dry_run and not token:
        raise RuntimeError(missing_token_message())

    candidates: list[dict[str, object]] = []
    for row in approved:
        asset = row.get("音效资源名", "").strip()
        prompt = row.get("prompt", "").strip()
        avoid = row.get("avoid", "").strip()
        if not asset or not prompt:
            raise ValueError("approved AI row requires 音效资源名 and prompt")
        text = f"{prompt} Avoid {avoid}." if avoid else prompt
        asset_dir = prod / "ai_candidates" / asset
        for variant in range(1, args.variants + 1):
            source = asset_dir / f"{asset}_ai_{variant:02d}.source.mp3"
            target = asset_dir / f"{asset}_ai_{variant:02d}.wav"
            if args.dry_run:
                print(f"dry run: {asset} variant={variant} -> {target}")
            else:
                generate_sound(
                    text,
                    base_url=args.base_url,
                    token=token,
                    output_path=source,
                    duration_seconds=args.duration,
                    prompt_influence=args.prompt_influence,
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run([
                    args.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(source), "-vn", "-acodec", "pcm_s16le", str(target),
                ], check=True)
            candidates.append({
                "assetName": asset, "variant": variant, "provider": "company_api",
                "sourcePath": str(source.relative_to(workspace)),
                "wavPath": str(target.relative_to(workspace)),
                "status": "planned" if args.dry_run else "generated",
                "prompt": text,
            })
            if args.delay and not args.dry_run:
                time.sleep(args.delay)
        row["status"] = "planned" if args.dry_run else "generated"

    manifest_path.write_text(json.dumps({
        "sheetName": args.sheet_name, "candidates": candidates,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.dry_run:
        write_csv(queue_path, rows, fields)
    print(f"AI candidates: {len(candidates)} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"AI gap generation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
