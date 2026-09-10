# -*- coding: utf-8 -*-
"""从三项目公用表结构工作簿读取指定 BI 表的字段定义。"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

STRUCTURE_NODE = "ZX6GRezwJl7zDo6zhnBEDKEpVdqbropQ"


def find_dws() -> str:
    w = shutil.which("dws")
    if w:
        return w
    import os

    home = os.path.expanduser("~")
    for p in (
        os.path.join(home, ".local", "bin", "dws.exe"),
        os.path.join(home, ".local", "bin", "dws"),
        r"C:\Software\Wukong\bin\dws.exe",
    ):
        if os.path.isfile(p):
            return p
    print("未找到 dws，请安装 DingTalk Workspace CLI", file=sys.stderr)
    sys.exit(1)


def dws_json(dws: str, *args: str) -> dict:
    r = subprocess.run(
        [dws, *args, "--format", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        sys.exit(r.returncode)
    return json.loads(r.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="读取 BI 表结构 Sheet 字段")
    parser.add_argument("--table", "-t", required=True, help="Sheet 名，如 user_asset")
    parser.add_argument("--range", default="A1:D50", help="读取范围")
    parser.add_argument("--node", default=STRUCTURE_NODE, help="表结构工作簿 nodeId")
    args = parser.parse_args()

    dws = find_dws()
    listing = dws_json(dws, "sheet", "list", "--node", args.node)
    sheet_id = None
    for s in listing.get("sheets", []):
        if s.get("name") == args.table:
            sheet_id = s["sheetId"]
            break
    if not sheet_id:
        names = [s.get("name") for s in listing.get("sheets", [])]
        print(f"未找到 Sheet: {args.table}\n可用: {names}", file=sys.stderr)
        sys.exit(1)

    data = dws_json(
        dws,
        "sheet",
        "range",
        "read",
        "--node",
        args.node,
        "--sheet-id",
        sheet_id,
        "--range",
        args.range,
    )
    rows = data.get("displayValues") or data.get("values") or []
    for row in rows:
        if any(str(c).strip() for c in row):
            print(" | ".join(str(c).replace("\r\n", " / ") for c in row[:4]))


if __name__ == "__main__":
    main()
