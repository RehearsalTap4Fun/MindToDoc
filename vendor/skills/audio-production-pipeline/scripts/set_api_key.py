#!/usr/bin/env python3
"""Write the company TTS api_key into this skill's private config.json.

Usage:
    python scripts/set_api_key.py tts_xxxxx

This keeps existing config fields, including jwt_token and tapper_auth_token.
Do not commit the generated config.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print("Usage: python scripts/set_api_key.py <api_key>")
        return 1

    api_key = sys.argv[1].strip()
    if not api_key.startswith("tts_"):
        print(f"Warning: api_key usually starts with 'tts_'; got '{api_key[:8]}...'. Writing it unchanged.")

    data = {}
    if CONFIG_PATH.is_file():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Could not read existing config.json; recreating it: {exc}")
            data = {}

    data["api_key"] = api_key
    data.setdefault("jwt_token", "")
    data.setdefault("tapper_auth_token", "")

    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote api_key to {CONFIG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
