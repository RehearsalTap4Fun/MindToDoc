#!/usr/bin/env python3
"""Download short company-library candidates for local browser playback."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from company_audio_api import DEFAULT_BASE_URL, load_token, missing_token_message
from workspace_paths import find_workspace_root


ROOT = find_workspace_root()


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")
    return value[:120] or "asset"


def duration(row: dict[str, str]) -> float:
    try:
        return float(row.get("duration_sec") or 0)
    except ValueError:
        return 0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def resolve_url(url: str, base_url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        base = urlparse(base_url)
        return urlunparse((base.scheme, base.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    return url


def download(url: str, token: str, timeout: float) -> bytes:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download_candidate(row: dict[str, str], base_url: str, assets_base_url: str, token: str, timeout: float) -> bytes:
    url = resolve_url(row["download_url"], base_url)
    try:
        return download(url, token, timeout)
    except Exception as first_error:
        candidate_id = row.get("candidate_id", "").strip()
        if not candidate_id:
            raise first_error
        fallback_url = f"{assets_base_url.rstrip('/')}/api/library/assets/{candidate_id}/download"
        try:
            return download(fallback_url, token, timeout)
        except Exception:
            raise first_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--assets-base-url", default="http://172.20.90.54:8401")
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument("--max-duration", type=float, default=3.0)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.output_dir.is_absolute():
        args.output_dir = (Path.cwd() / args.output_dir).resolve()
    if not args.manifest.is_absolute():
        args.manifest = (Path.cwd() / args.manifest).resolve()

    token = load_token(args.config_dir)
    if not token:
        raise SystemExit(missing_token_message())

    rows = read_csv(args.candidates)
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        candidate_id = row.get("candidate_id", "")
        if not candidate_id:
            continue
        dur = duration(row)
        if not (0 < dur <= args.max_duration):
            continue
        unique.setdefault(candidate_id, row)

    items = list(unique.values())
    items.sort(key=lambda row: (duration(row), row.get("candidate_id", "")))
    if args.limit:
        items = items[: args.limit]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    preview_map: dict[str, dict[str, str]] = {}
    ok = 0
    failed = 0
    for index, row in enumerate(items, 1):
        candidate_id = row["candidate_id"]
        filename = row.get("filename") or f"{candidate_id}.wav"
        ext = Path(filename).suffix or ".wav"
        target = args.output_dir / f"{candidate_id}_{safe_name(Path(filename).stem)}{ext}"
        status = "exists"
        error = ""
        if args.force or not target.exists() or target.stat().st_size == 0:
            try:
                data = download_candidate(row, args.base_url, args.assets_base_url, token, args.timeout)
                target.write_bytes(data)
                status = "downloaded"
            except Exception as exc:
                failed += 1
                error = str(exc)
                print(f"[{index}/{len(items)}] failed {candidate_id}: {error}", file=sys.stderr, flush=True)
                preview_map[candidate_id] = {
                    "status": "failed",
                    "error": error,
                    "local_path": "",
                    "relative_path": "",
                }
                continue
        ok += 1
        rel = target.relative_to(ROOT).as_posix()
        preview_map[candidate_id] = {
            "status": status,
            "error": "",
            "local_path": str(target),
            "relative_path": "/" + rel,
        }
        print(f"[{index}/{len(items)}] {status} {candidate_id} -> {rel}", flush=True)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(preview_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.manifest}")
    print(f"Candidates considered: {len(items)} ok={ok} failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
