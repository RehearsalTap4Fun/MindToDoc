#!/usr/bin/env python3
"""把钉钉文档导出的 markdown 反转义为本地干净 markdown。

钉钉 `get_document_content(format=markdown)` 返回的 GFM 严格转义,直接写到本地文件
会出现满屏 `\\+` `\\*\\*` `\\{` 等,渲染成正文反斜杠或 markdown 失效。本脚本做最小
反转义,使两边互转的差异收敛到只剩业务内容。

详细规则见 memory/dingtalk-md-escape-diff.md。

用法
----
读 stdin、写 stdout:
    python scripts/dingtalk_md_unescape.py < raw.md > clean.md

读文件、写文件(就地覆盖):
    python scripts/dingtalk_md_unescape.py raw.md
    python scripts/dingtalk_md_unescape.py raw.md -o clean.md

校验模式(只检查不写,有残留 token 时退出码=1,适合 CI):
    python scripts/dingtalk_md_unescape.py --check raw.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# 顺序敏感:先处理 2 字符序列,再处理单字符,最后处理 \\\\,否则会过度还原
_REPLACEMENTS = [
    (r"\+", "+"),
    (r"\*\*", "**"),
    (r"\*", "*"),
    (r"\{", "{"),
    (r"\}", "}"),
    (r"\[", "["),
    (r"\]", "]"),
    (r"\\", "\\"),       # 必须放在最后
    ("&#91;", "["),
    ("&#93;", "]"),
]

# 校验时扫描的残留 token(干净本地 md 不应出现)
_RESIDUAL_TOKENS = [r"\+", r"\*\*", r"\{", r"\}", r"\[", r"\]", "&#91;", "&#93;"]


def unescape(text: str) -> str:
    for src, dst in _REPLACEMENTS:
        text = text.replace(src, dst)
    return text


def scan_residuals(text: str) -> dict[str, int]:
    """返回每个残留 token 的出现次数,全 0 表示干净。"""
    return {tok: text.count(tok) for tok in _RESIDUAL_TOKENS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DingTalk markdown 反转义")
    parser.add_argument("input", nargs="?", help="输入文件;省略读 stdin")
    parser.add_argument("-o", "--output", help="输出文件;省略时:有 input 则就地覆盖,无 input 则写 stdout")
    parser.add_argument("--check", action="store_true",
                        help="只校验不写;发现残留转义 token 退出码=1")
    args = parser.parse_args(argv)

    if args.input:
        raw = Path(args.input).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if args.check:
        residuals = scan_residuals(raw)
        bad = {k: v for k, v in residuals.items() if v}
        if bad:
            print("发现残留转义 token:", file=sys.stderr)
            for k, v in bad.items():
                print(f"  {k!r}: {v} 处", file=sys.stderr)
            return 1
        print("OK: 无残留转义 token", file=sys.stderr)
        return 0

    cleaned = unescape(raw)

    if args.output:
        Path(args.output).write_text(cleaned, encoding="utf-8")
    elif args.input:
        Path(args.input).write_text(cleaned, encoding="utf-8")
    else:
        sys.stdout.write(cleaned)
    return 0


if __name__ == "__main__":
    sys.exit(main())
