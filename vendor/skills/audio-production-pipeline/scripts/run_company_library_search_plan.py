#!/usr/bin/env python3
"""Run a company-library search plan CSV and write reviewable results."""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from company_audio_api import DEFAULT_BASE_URL, load_token, missing_token_message


DETAIL_FIELDS = [
    "request_id",
    "event_name",
    "asset_name",
    "query_rank",
    "library_query",
    "search_status",
    "total",
    "candidate_rank",
    "candidate_id",
    "filename",
    "duration_sec",
    "project_code",
    "category_path",
    "tags_clean",
    "download_url",
    "planner_decision",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id", ""),
        "filename": item.get("filename", ""),
        "duration_sec": item.get("duration_sec", ""),
        "project_code": item.get("project_code", ""),
        "category_path": item.get("category_path", ""),
        "tags_clean": item.get("tags_clean", ""),
        "download_url": item.get("download_url", ""),
    }


def search_library_with_timeout(
    query: str,
    *,
    base_url: str,
    token: str,
    limit: int,
    mode: str,
    asset_type: str,
    duration_bucket: str,
    timeout: float,
) -> dict[str, Any]:
    body: dict[str, Any] = {"query": query, "mode": mode, "limit": limit}
    if asset_type:
        body["asset_types"] = [asset_type]
    if duration_bucket:
        body["duration_bucket"] = duration_bucket
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/library/search",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def flush(json_path: Path, csv_path: Path, raw_results: list[dict[str, Any]], detail_rows: list[dict[str, Any]]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(raw_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, detail_rows, DETAIL_FIELDS)


def run_plan(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not args.allow_unapproved_demand:
        review_path = args.search_plan.parent / "planner_demand_review.json"
        if review_path.exists():
            try:
                review = json.loads(review_path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                raise SystemExit(f"Invalid planner demand review file: {review_path} ({exc})")
            status = str(review.get("status") or "").strip()
            if status != "approved":
                raise SystemExit(
                    "Planner demand review is not approved. "
                    f"Open {review_path.parent / 'audio_demand.xlsx'} and "
                    f"{review_path.parent / 'planner_demand_review.md'} first, "
                    "then set planner_demand_review.json status to approved. "
                    "For technical dry runs only, pass --allow-unapproved-demand."
                )
    token = load_token(args.config_dir)
    if not token:
        raise SystemExit(missing_token_message())

    plan_rows = read_csv(args.search_plan)
    if args.start:
        plan_rows = plan_rows[args.start :]
    if args.max_rows:
        plan_rows = plan_rows[: args.max_rows]

    raw_results: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []

    for index, row in enumerate(plan_rows, 1):
        query = row.get("library_query", "").strip()
        status = "ok"
        result: dict[str, Any] = {}
        items: list[dict[str, Any]] = []
        error = ""
        if not query:
            status = "skipped_empty_query"
        else:
            try:
                result = search_library_with_timeout(
                    query,
                    base_url=args.base_url,
                    token=token,
                    limit=args.limit,
                    mode=args.mode,
                    asset_type=args.asset_type,
                    duration_bucket=args.duration_bucket,
                    timeout=args.timeout,
                )
                items = result.get("items", []) or []
            except Exception as exc:  # Keep the batch moving; planner can retry failed rows.
                status = "error"
                error = str(exc)

        raw_results.append(
            {
                **row,
                "search_status": status,
                "total": result.get("total", 0),
                "items": [compact_item(item) for item in items],
                "interpretation": result.get("interpretation", {}),
                "error": error,
            }
        )
        if items:
            for candidate_rank, item in enumerate(items, 1):
                detail_rows.append(
                    {
                        **row,
                        "search_status": status,
                        "total": result.get("total", 0),
                        "candidate_rank": candidate_rank,
                        "candidate_id": item.get("id", ""),
                        "filename": item.get("filename", ""),
                        "duration_sec": item.get("duration_sec", ""),
                        "project_code": item.get("project_code", ""),
                        "category_path": item.get("category_path", ""),
                        "tags_clean": item.get("tags_clean", ""),
                        "download_url": item.get("download_url", ""),
                        "planner_decision": "",
                    }
                )
        else:
            detail_rows.append(
                {
                    **row,
                    "search_status": status,
                    "total": result.get("total", 0),
                    "candidate_rank": "",
                    "candidate_id": "",
                    "filename": "",
                    "duration_sec": "",
                    "project_code": "",
                    "category_path": error,
                    "tags_clean": "",
                    "download_url": "",
                    "planner_decision": "no_company_candidate" if status == "ok" else "search_failed",
                }
            )

        if args.flush_every and index % args.flush_every == 0:
            flush(args.output_json, args.output_csv, raw_results, detail_rows)
            print(f"Flushed {index}/{len(plan_rows)} searches")
        if args.progress_every and index % args.progress_every == 0:
            print(
                f"Progress {index}/{len(plan_rows)} status={status} "
                f"items={len(items)} query={query[:70]}",
                flush=True,
            )
        if args.delay:
            time.sleep(args.delay)

    return raw_results, detail_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("search_plan", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--mode", choices=["ai", "normal"], default="ai")
    parser.add_argument("--asset-type", default="sfx")
    parser.add_argument("--duration-bucket", default="")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--flush-every", type=int, default=10)
    parser.add_argument("--progress-every", type=int, default=1)
    parser.add_argument("--allow-unapproved-demand", action="store_true")
    args = parser.parse_args()

    raw_results, detail_rows = run_plan(args)
    flush(args.output_json, args.output_csv, raw_results, detail_rows)
    ok = sum(1 for row in raw_results if row.get("search_status") == "ok")
    errors = sum(1 for row in raw_results if row.get("search_status") == "error")
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_csv}")
    print(f"Searches: {len(raw_results)} ok={ok} errors={errors} candidate_rows={len(detail_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
