#!/usr/bin/env python3
"""Company audio API adapter for X15 Audio Forge.

This module intentionally separates:
- library search: safe to run automatically, no downloads
- library download: not implemented here; require explicit user confirmation
- sound generation: saves AI-generated previews from /api/sound

The company /api/sound endpoint expects English text. Callers should provide
prompt_en or prompt; do not pass Chinese descriptions directly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse


DEFAULT_BASE_URL = os.environ.get("TAPPER_AUDIO_BASE_URL", "http://172.20.90.54:8001")
API_KEY_LOGIN_URL = "https://voiceclone.tap4fun.com/auth/apikey-login"


def missing_token_message() -> str:
    return (
        "Missing company audio token. OpenClaw injects TAPPER_AUTH_TOKEN automatically. "
        "For Codex/Claude Code/local use, open "
        f"{API_KEY_LOGIN_URL} with your company account, copy the api_key shown there, "
        "then run: python scripts/set_api_key.py <api_key>. "
        "The tool reads tokens in this order: TAPPER_AUTH_TOKEN, config.json api_key, "
        "config.json jwt_token, config.json tapper_auth_token."
    )


def load_token(config_dir: Path | None = None) -> str:
    token = os.environ.get("TAPPER_AUTH_TOKEN", "").strip()
    if token:
        return token

    candidates: list[Path] = []
    if config_dir:
        candidates.append(config_dir / "config.json")
    candidates.append(Path(__file__).resolve().parents[1] / "config.json")

    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for field in ("api_key", "jwt_token", "tapper_auth_token"):
            token = (data.get(field) or "").strip()
            if token and token not in {"xxxxx", "<paste_token_after_TAPPER_AUTH_TOKEN_equals>"}:
                return token
    return ""


def request_json(base_url: str, path: str, token: str, body: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"{path} failed HTTP {exc.code}: {detail}") from exc


def download_bytes(url: str, token: str = "") -> bytes:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def resolve_api_url(url: str, base_url: str) -> str:
    """Rewrite API-provided localhost URLs so they are reachable from this client."""
    parsed = urlparse(url)
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        base = urlparse(base_url)
        netloc = base.netloc
        return urlunparse((base.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    return url


def search_library(
    query: str,
    *,
    base_url: str,
    token: str,
    limit: int = 5,
    mode: str = "ai",
    asset_type: str = "sfx",
    duration_bucket: str = "",
) -> dict[str, Any]:
    body: dict[str, Any] = {"query": query, "mode": mode, "limit": limit}
    if asset_type:
        body["asset_types"] = [asset_type]
    if duration_bucket:
        body["duration_bucket"] = duration_bucket
    return request_json(base_url, "/api/library/search", token, body)


def generate_sound(
    text_en: str,
    *,
    base_url: str,
    token: str,
    output_path: Path,
    duration_seconds: float = 0,
    prompt_influence: float = 0.3,
) -> dict[str, Any]:
    body = {
        "text": text_en,
        "prompt_influence": prompt_influence,
    }
    if duration_seconds >= 0.5:
        body["duration_seconds"] = min(duration_seconds, 30)
    result = request_json(base_url, "/api/sound", token, body)
    audio_url = result.get("audio_url")
    if not audio_url:
        raise RuntimeError(f"/api/sound did not return audio_url: {result}")
    audio_url = resolve_api_url(audio_url, base_url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(download_bytes(audio_url, token))
    return result


def iter_sound_design_rows(data: dict[str, Any]):
    for sheet in data.get("sheets", []):
        for row in sheet.get("rows", []):
            if row.get("type") in {"module", "submod"}:
                continue
            yield sheet, row


def prompt_for_row(row: dict[str, Any]) -> str:
    for key in ("prompt_en", "prompt", "text_en"):
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def build_search_query(row: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in [
            row.get("prompt_en") or row.get("prompt") or "",
            row.get("desc") or "",
            row.get("bank") or "",
            row.get("trigger") or "",
        ]
        if str(part).strip()
    )


def cmd_search(args: argparse.Namespace) -> int:
    token = load_token(args.config_dir)
    if not token:
        print(missing_token_message(), file=sys.stderr)
        return 2
    result = search_library(
        args.query,
        base_url=args.base_url,
        token=token,
        limit=args.limit,
        mode=args.mode,
        asset_type=args.asset_type,
        duration_bucket=args.duration_bucket,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    token = load_token(args.config_dir)
    if not token:
        print(missing_token_message(), file=sys.stderr)
        return 2
    result = generate_sound(
        args.text,
        base_url=args.base_url,
        token=token,
        output_path=args.output,
        duration_seconds=args.duration,
        prompt_influence=args.prompt_influence,
    )
    print(json.dumps({"output": str(args.output), **result}, ensure_ascii=False, indent=2))
    return 0


def cmd_batch_generate(args: argparse.Namespace) -> int:
    token = load_token(args.config_dir)
    if not token:
        print(missing_token_message(), file=sys.stderr)
        return 2
    data = json.loads(args.data_json.read_text(encoding="utf-8"))
    out_dir = args.output_dir
    manifest: list[dict[str, Any]] = []
    rows = [row for _, row in iter_sound_design_rows(data) if row.get("tag") == "新增"]

    for row in rows:
        asset = row.get("asset") or row.get("event")
        prompt = prompt_for_row(row)
        if not prompt:
            manifest.append({"asset": asset, "event": row.get("event"), "status": "skipped_missing_english_prompt"})
            continue
        for variant in range(1, args.variants + 1):
            output = out_dir / f"{asset}_ai_{variant:02d}.mp3"
            if output.exists() and not args.force:
                status = "exists"
            else:
                try:
                    result = generate_sound(
                        prompt,
                        base_url=args.base_url,
                        token=token,
                        output_path=output,
                        duration_seconds=args.duration,
                        prompt_influence=args.prompt_influence,
                    )
                    status = "generated"
                except Exception as exc:
                    manifest.append(
                        {
                            "asset": asset,
                            "event": row.get("event"),
                            "variant": variant,
                            "status": "failed",
                            "error": str(exc),
                        }
                    )
                    continue
                if args.delay and variant < args.variants:
                    time.sleep(args.delay)
            manifest.append(
                {
                    "asset": asset,
                    "event": row.get("event"),
                    "variant": variant,
                    "prompt_en": prompt,
                    "status": status,
                    "file": str(output),
                }
            )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.manifest}")
    return 0


def cmd_batch_search(args: argparse.Namespace) -> int:
    token = load_token(args.config_dir)
    if not token:
        print(missing_token_message(), file=sys.stderr)
        return 2
    data = json.loads(args.data_json.read_text(encoding="utf-8"))
    results = []
    for _, row in iter_sound_design_rows(data):
        query = build_search_query(row)
        if not query:
            continue
        try:
            result = search_library(
                query,
                base_url=args.base_url,
                token=token,
                limit=args.limit,
                mode=args.mode,
                asset_type=args.asset_type,
                duration_bucket=args.duration_bucket,
            )
            items = result.get("items", [])
            results.append(
                {
                    "event": row.get("event"),
                    "asset": row.get("asset"),
                    "query": query,
                    "total": result.get("total", 0),
                    "must_empty": result.get("interpretation", {}).get("must_empty", False),
                    "items": items,
                    "interpretation": result.get("interpretation", {}),
                }
            )
        except Exception as exc:
            results.append({"event": row.get("event"), "asset": row.get("asset"), "query": query, "error": str(exc)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="X15 company audio API adapter")
    parser.add_argument("--base-url", default=os.environ.get("TTS_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--config-dir", type=Path, default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    search = sub.add_parser("search-library")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--mode", choices=["ai", "normal"], default="ai")
    search.add_argument("--asset-type", default="sfx")
    search.add_argument("--duration-bucket", default="")
    search.set_defaults(func=cmd_search)

    gen = sub.add_parser("generate-sound")
    gen.add_argument("text", help="English sound prompt")
    gen.add_argument("output", type=Path)
    gen.add_argument("--duration", type=float, default=0)
    gen.add_argument("--prompt-influence", type=float, default=0.3)
    gen.set_defaults(func=cmd_generate)

    batch_gen = sub.add_parser("batch-generate-sounds")
    batch_gen.add_argument("data_json", type=Path)
    batch_gen.add_argument("output_dir", type=Path)
    batch_gen.add_argument("--manifest", type=Path, required=True)
    batch_gen.add_argument("--variants", type=int, default=2)
    batch_gen.add_argument("--duration", type=float, default=0)
    batch_gen.add_argument("--prompt-influence", type=float, default=0.3)
    batch_gen.add_argument("--delay", type=float, default=0.5)
    batch_gen.add_argument("--force", action="store_true")
    batch_gen.set_defaults(func=cmd_batch_generate)

    batch_search = sub.add_parser("batch-search-library")
    batch_search.add_argument("data_json", type=Path)
    batch_search.add_argument("output", type=Path)
    batch_search.add_argument("--limit", type=int, default=5)
    batch_search.add_argument("--mode", choices=["ai", "normal"], default="ai")
    batch_search.add_argument("--asset-type", default="sfx")
    batch_search.add_argument("--duration-bucket", default="")
    batch_search.set_defaults(func=cmd_batch_search)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except urllib.error.URLError as exc:
        print(f"Network/API error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
