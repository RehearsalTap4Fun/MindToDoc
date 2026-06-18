#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫 references/ 目录下所有 markdown,统计未填的 TBD 项。

用法:
    python scripts/list_tbd.py
    python scripts/list_tbd.py --root references --threshold 10

输出:
    - markdown 表格:文档 / TBD 数 / 文档大小 / 最早 anchor 日期(若 frontmatter 含)
    - 当某文档 TBD 数 >= --threshold 时,标 [WARN] 提示拉清单会议

设计:
- 识别两种模式:
  1. 强匹配 `**TBD-数字**:` 或 `**TBD-字母数字**:`(如 `**TBD-0a**:`)— 协议章节内编号 TBD
  2. 弱匹配 `TBD`(独立单词,大小写敏感) — 含表格里的「TBD」单元格
- 强匹配按编号去重(同 TBD-3 引用多次只算一项),弱匹配按行去重。
- 跳过代码块内的 TBD(避免误判 plan / 工具说明里的示例)。
- 仅扫文本文件(.md),按字母序输出,GBK 控制台输出 ASCII 安全。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CODE_FENCE = re.compile(r"^```")
TBD_NUMBERED = re.compile(r"\*\*TBD-([0-9a-zA-Z]+)\*\*\s*[::]")
TBD_LOOSE = re.compile(r"(?<![A-Za-z_])TBD(?![A-Za-z_])")


def strip_code_blocks(lines: list[str]) -> list[tuple[int, str]]:
    """剥离 ``` 围栏内的代码块,返回 [(line_no, content), ...]。"""
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(lines, 1):
        if CODE_FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        out.append((i, line))
    return out


def scan_file(path: Path) -> dict:
    """返回 {numbered: set[str], loose_lines: list[(lineno, snippet)], total_lines: int}。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    visible = strip_code_blocks(lines)
    numbered: set[str] = set()
    loose: list[tuple[int, str]] = []
    for lineno, line in visible:
        for m in TBD_NUMBERED.finditer(line):
            numbered.add(m.group(1))
        if TBD_LOOSE.search(line) and not TBD_NUMBERED.search(line):
            snippet = line.strip()[:80]
            loose.append((lineno, snippet))
    return {
        "numbered": numbered,
        "loose": loose,
        "total_lines": len(lines),
    }


def format_report(results: dict[Path, dict], root: Path, threshold: int) -> str:
    out: list[str] = []
    out.append(f"# TBD 状态索引 · {root}")
    out.append("")
    out.append(f"扫描根目录:`{root}`")
    out.append(f"阈值:{threshold}(超过则标 WARN)")
    out.append("")
    out.append("| 文档 | 编号 TBD | 散落 TBD | 文件行数 | 状态 |")
    out.append("|------|---------:|---------:|---------:|------|")
    total_numbered = 0
    total_loose = 0
    docs_over_threshold: list[Path] = []
    for path in sorted(results.keys()):
        r = results[path]
        n = len(r["numbered"])
        l = len(r["loose"])
        total_numbered += n
        total_loose += l
        if n >= threshold:
            status = "[WARN] 拉清单会议"
            docs_over_threshold.append(path)
        elif n + l > 0:
            status = "open"
        else:
            status = "ok"
        rel = path.relative_to(root.parent) if path.is_relative_to(root.parent) else path
        out.append(f"| `{rel}` | {n} | {l} | {r['total_lines']} | {status} |")
    out.append(f"| **合计** | **{total_numbered}** | **{total_loose}** | — | — |")
    out.append("")
    if docs_over_threshold:
        out.append("## 超阈值文档详情")
        out.append("")
        for path in docs_over_threshold:
            r = results[path]
            out.append(f"### `{path}`")
            out.append("")
            out.append(f"编号 TBD ({len(r['numbered'])}):{sorted(r['numbered'])}")
            out.append("")
            if r["loose"]:
                out.append(f"散落 TBD ({len(r['loose'])}):")
                for lineno, snippet in r["loose"][:10]:
                    out.append(f"- L{lineno}: `{snippet}`")
                if len(r["loose"]) > 10:
                    out.append(f"- ...(还有 {len(r['loose']) - 10} 条)")
                out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="扫 references/*.md 统计 TBD")
    parser.add_argument("--root", type=Path, default=Path("references"),
                        help="扫描根目录(默认 references/)")
    parser.add_argument("--threshold", type=int, default=10,
                        help="编号 TBD 数 >= 此值时标 WARN(默认 10)")
    parser.add_argument("--ext", default=".md", help="文件扩展名(默认 .md)")
    args = parser.parse_args(argv)

    root: Path = args.root
    if not root.exists():
        print(f"[error] 根目录不存在: {root}", file=sys.stderr)
        return 2

    paths = sorted(root.rglob(f"*{args.ext}"))
    if not paths:
        print(f"[info] {root} 下无 {args.ext} 文件")
        return 0

    results: dict[Path, dict] = {p: scan_file(p) for p in paths}
    print(format_report(results, root, args.threshold))
    return 0


if __name__ == "__main__":
    sys.exit(main())
