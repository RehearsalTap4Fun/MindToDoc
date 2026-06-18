"""dingtalk_table_inserter — 自动出补表执行计划

输入：
  --blocks   list_document_blocks 的 JSON 输出（可整段保存到文件）
  --tables   md2jsonml 生成的 tables sidecar (.jsonml.tables.json)
  --node-id  目标钉钉节点 ID（仅用于在计划里打印，不真正调 API）
  --marker   占位字符前缀，默认 〚TBL-（旧版兼容用 TABLE_）
  --out      执行计划输出路径（默认 stdout）

输出：一份 JSON 计划，按 anchor blk_idx **倒序**排列，每个 anchor 内多张表按
table_idx **DESC** 排列；每条记录包含一次 append（插表）和一次 update_block 或
delete_block（清占位）。本脚本只生成计划，**不调用 MCP**——把计划喂给上层 agent 执行。

设计要点
--------
1. 倒序处理 anchor，确保上方 anchor 的 blk_idx 不被下方插入污染。
2. 同 anchor 内多表：按 table_idx 降序逐张插到 anchor.blk_idx + 1
   （第一张落在最远处，最后一张紧贴 anchor，文档里最终是升序）。
3. anchor 占位文本只剩 marker 时整段删除；含正文时改写去除 marker。
4. 占位字符默认是新版 〚TBL-N〛；旧文档 TABLE_N 兼容传 --marker TABLE_。

用法示例
--------
  list_document_blocks 输出保存到 blocks.json:
    cat > blocks.json << 'EOF'
    { "blocks": [...] }
    EOF
  python scripts/dingtalk_table_inserter.py \\
    --blocks blocks.json \\
    --tables output/dingtalk-sync/main.jsonml.tables.json \\
    --node-id qnYMoO1rWxDrlovrUjaPlzMYW47Z3je9 \\
    --out plan.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def extract_text(block: dict) -> tuple[str, str]:
    """Return (block_type, text)."""
    el = block.get("element", block)
    btype = block.get("blockType") or el.get("blockType") or ""
    if btype == "paragraph":
        return btype, el.get("paragraph", {}).get("text", "")
    if btype == "unorderedList":
        return btype, el.get("unorderedList", {}).get("text", "")
    if btype == "heading":
        return btype, el.get("heading", {}).get("text", "")
    if btype == "blockquote":
        # blockquote 不支持 update_document_block，但仍要识别其文本以防 marker 落在里面
        bq = el.get("blockquote", {})
        return btype, bq.get("text", "") if isinstance(bq, dict) else ""
    return btype, ""


def parse_blocks(blocks_path: Path) -> list[dict]:
    raw = json.loads(blocks_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "blocks" in raw:
        return raw["blocks"]
    if isinstance(raw, list):
        return raw
    raise ValueError(f"Unexpected blocks JSON shape in {blocks_path}")


def find_placeholders(
    blocks: list[dict], marker_prefix: str
) -> list[tuple[int, int, str, str, str]]:
    """Locate (table_idx, blk_idx, blk_id, btype, full_text) for each placeholder.

    A block may contain multiple TABLE markers — each occurrence becomes its own
    placeholder record (with same blk_idx/blk_id/text but different table_idx).
    """
    # Build regex from marker_prefix; support legacy "TABLE_" and new "〚TBL-".
    if marker_prefix == "〚TBL-":
        pattern = re.compile(r"〚TBL-(\d+)〛")
    elif marker_prefix == "TABLE_":
        pattern = re.compile(r"TABLE_(\d+)")
    else:
        # Custom prefix: assume <prefix><digits>
        pattern = re.compile(re.escape(marker_prefix) + r"(\d+)")

    out: list[tuple[int, int, str, str, str]] = []
    for blk in blocks:
        el = blk.get("element", blk)
        blk_idx = el.get("index", blk.get("index"))
        blk_id = el.get("id", "")
        btype, text = extract_text(blk)
        if not text:
            continue
        matches = pattern.findall(text)
        for ti in matches:
            out.append((int(ti), blk_idx, blk_id, btype, text))
    return out


def build_plan(
    placeholders: list[tuple[int, int, str, str, str]],
    tables_md: list[str],
    marker_prefix: str,
    node_id: str,
) -> list[dict]:
    """Group by anchor blk_id; emit ordered ops."""
    if marker_prefix == "〚TBL-":
        token_re = re.compile(r"〚TBL-\d+〛")
    elif marker_prefix == "TABLE_":
        token_re = re.compile(r"TABLE_\d+")
    else:
        token_re = re.compile(re.escape(marker_prefix) + r"\d+")

    groups: dict[str, dict] = defaultdict(
        lambda: {"blk_idx": None, "blk_id": None, "btype": None, "text": None, "tables": []}
    )
    for ti, bi, bid, bt, txt in placeholders:
        g = groups[bid]
        g["blk_idx"] = bi
        g["blk_id"] = bid
        g["btype"] = bt
        g["text"] = txt
        g["tables"].append(ti)

    # Anchor order: largest blk_idx first (process bottom-up so upper anchors
    # don't shift). Within an anchor: table_idx DESC so smaller-idx tables end
    # up adjacent to anchor → final document order ascends.
    anchor_list = sorted(groups.values(), key=lambda g: -g["blk_idx"])

    ops: list[dict] = []
    for grp in anchor_list:
        grp["tables"].sort(reverse=True)
        anchor_idx = grp["blk_idx"]
        for ti in grp["tables"]:
            if ti >= len(tables_md):
                ops.append(
                    {"op": "warn", "reason": f"table_idx {ti} out of range; sidecar has {len(tables_md)} tables"}
                )
                continue
            ops.append(
                {
                    "op": "append_table",
                    "node_id": node_id,
                    "table_idx": ti,
                    "after_blk_idx": anchor_idx,
                    "insert_index": anchor_idx + 1,
                    "markdown": tables_md[ti],
                    "anchor_blk_id": grp["blk_id"],
                }
            )
        # After all tables for this anchor inserted, clean placeholder text
        new_text = token_re.sub("", grp["text"]).strip()
        if not new_text:
            ops.append(
                {
                    "op": "delete_block",
                    "node_id": node_id,
                    "blk_id": grp["blk_id"],
                    "btype": grp["btype"],
                    "reason": "standalone placeholder",
                }
            )
        else:
            ops.append(
                {
                    "op": "update_block",
                    "node_id": node_id,
                    "blk_id": grp["blk_id"],
                    "btype": grp["btype"],
                    "new_text": new_text,
                }
            )
    return ops


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--blocks", required=True, type=Path, help="list_document_blocks JSON dump")
    p.add_argument("--tables", required=True, type=Path, help="md2jsonml tables sidecar")
    p.add_argument("--node-id", required=True, help="dingtalk node id (informational)")
    p.add_argument("--marker", default="〚TBL-", help="placeholder prefix (default 〚TBL-, legacy TABLE_)")
    p.add_argument("--out", type=Path, help="output plan JSON path (default stdout)")
    args = p.parse_args()

    blocks = parse_blocks(args.blocks)
    tables_md = json.loads(args.tables.read_text(encoding="utf-8"))
    placeholders = find_placeholders(blocks, args.marker)
    if not placeholders:
        print(f"[warn] no placeholders found with marker prefix {args.marker!r}", file=sys.stderr)
    plan = build_plan(placeholders, tables_md, args.marker, args.node_id)

    summary = {
        "node_id": args.node_id,
        "marker_prefix": args.marker,
        "total_placeholders": len(placeholders),
        "total_tables_in_sidecar": len(tables_md),
        "anchors": len({p["anchor_blk_id"] if p["op"] == "append_table" else p.get("blk_id") for p in plan if p.get("op") in {"append_table", "delete_block", "update_block"}}),
        "ops": plan,
    }

    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
        print(f"plan written: {args.out} ({len(plan)} ops, {summary['total_placeholders']} placeholders)", file=sys.stderr)
    else:
        sys.stdout.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
