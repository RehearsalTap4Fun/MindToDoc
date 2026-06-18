# -*- coding: utf-8 -*-
"""md → 完整 jsonml 转换器（A 方案）。
读设计文档 md，输出整篇 jsonml（每个块带好 ind.left，每个标题带好 list 自动编号），
供 update_document(format=jsonml) 一次性 overwrite 写全；同时输出大文档 markdown 主体。

支持的 md 元素：
- 注释 <!-- --> ：跳过（md 给人看的元数据，不进钉钉）
- 图片占位 <!-- IMG: 界面名 | image_id --> ：转成 〚IMG-N〛 占位段，并写入 images sidecar
- # / ## / ### 标题：转 h1/h2/h3，全部带 list 编号 + ind.left（H1=0,H2=32,H3=64）
- 两级无序列表（- 项 / 两空格缩进 - 子项）：转 p+list bullet，ind = 所属标题正文档(标题+32)，二级再+? 这里列表本身有 level，ind 用所属标题的正文档值
- 普通段落：转 p，ind = 所属标题正文档值
- 表格 | a | b |：转 〚TBL-N〛 占位段（前后留空行），并写入 tables sidecar
- 图片占位 <!-- IMG: 界面名 | image_id --> ：转成 〚IMG-N〛 占位段（前后留空行），并写入 images sidecar
- 大文档 markdown 主体：输出 <out>.body.md，保留 〚TBL-N〛 / 〚IMG-N〛 占位
- 行内格式：**加粗**、{{red:红字}}

ind 规则（正文比标题多缩一档，每级 32）：
- H1 标题 ind=0，其下正文/列表 ind=32
- H2 标题 ind=32，其下正文/列表 ind=64
- H3 标题 ind=64，其下正文 ind=96
"""
import sys, json, re

SRC = sys.argv[1]
OUT = sys.argv[2]
LIST_ID = sys.argv[3] if len(sys.argv) > 3 else "doc-h"

lines = open(SRC, encoding="utf-8").read().split("\n")

blocks = []
cur_heading_level = 0  # 当前所属标题级别（0=文档顶，无标题）
tables_md = []           # 表格 markdown 列表，占位段文本为 〚TBL-i〛
images_md = []           # 图片占位元数据，占位段文本为 〚IMG-i〛
body_lines = []          # 大文档 markdown overwrite 主体，保留 TABLE/IMG 占位
i = 0
n = len(lines)

# 列表上下文：连续列表行共享一个 listId
list_counter = [0]
def new_list_id():
    list_counter[0] += 1
    return f"ul{list_counter[0]}"

def body_ind(hlevel):
    # 正文 ind = 标题ind + 32；标题ind = (level-1)*32
    if hlevel == 0:
        return 0
    return (hlevel - 1) * 32 + 32

def heading_ind(level):
    return (level - 1) * 32

def leaf(text, bold=False, color=None):
    span = {"data-type": "leaf"}
    if bold:
        span["bold"] = True
    if color:
        span["color"] = color
    return ["span", {"data-type": "text"}, ["span", span, text]]

def inline_nodes(text):
    """Parse the two supported inline formats: **bold** and {{red:text}}."""
    nodes = []
    token_re = re.compile(r"(\{\{red:.*?\}\}|\*\*.*?\*\*)")
    pos = 0
    for m in token_re.finditer(text):
        if m.start() > pos:
            nodes.append(leaf(text[pos:m.start()]))
        tok = m.group(0)
        if tok.startswith("{{red:"):
            nodes.append(leaf(tok[6:-2], color="#FE0300"))
        else:
            nodes.append(leaf(tok[2:-2], bold=True))
        pos = m.end()
    if pos < len(text):
        nodes.append(leaf(text[pos:]))
    return nodes or [leaf("")]

def heading_block(level, text, numbered=True):
    sz = 21 if level == 1 else (18 if level == 2 else 16)
    attrs = {"ind": {"hanging": 0, "left": heading_ind(level)}}
    if numbered:
        fmt = ".".join(f"%{k}" for k in range(1, level + 1))
        attrs["list"] = {"listId": LIST_ID, "level": level - 1, "isOrdered": True,
                         "autoLevel": True, "listStyleType": "DEC_DEC_DEC_P",
                         "symbolStyle": {"sz": sz, "bold": True},
                         "listStyle": {"format": "decimal", "text": fmt, "align": "left"}}
    return ["h%d" % level, attrs] + inline_nodes(text)

def para_block(text, hlevel):
    return ["p", {"ind": {"hanging": 0, "left": body_ind(hlevel)}}] + inline_nodes(text)

def list_block(text, level, listid, ordered, hlevel):
    # level: 0=一级 1=二级；ind 用正文档 + 二级再加一档
    ind = body_ind(hlevel) + (32 if level == 1 else 0)
    sym = "●" if level == 0 else "○"
    return ["p", {
        "ind": {"hanging": 0, "left": ind},
        "list": {"listId": listid, "isOrdered": False, "level": level,
                 "listStyle": {"format": "bullet", "text": sym, "align": "left"}}
    }] + inline_nodes(text)

def table_block(rows, hlevel):
    # rows: list of list[str]；首行加粗当表头
    # 必须带 tblW(pct) + 每个 tc 的 rowSpan/colSpan，否则窄的纯文字表会被钉钉降级成 columns 分栏块
    ncol = len(rows[0])
    pct = int(100 / ncol)
    colw = [pct] * ncol
    tbl = ["table", {"colsWidth": colw, "tblW": {"type": "pct"}, "styleId": "tableHeader", "sr": True,
                     "tblLook": {"firstRow": 1, "lastRow": 0, "firstColumn": 0, "lastColumn": 0}}]
    for ri, row in enumerate(rows):
        tr_attr = {"isTblHeader": True} if ri == 0 else {}
        tr = ["tr", tr_attr]
        for cell in row:
            tr.append(["tc", {"rowSpan": 1, "colSpan": 1}, ["p", {}, leaf(cell.strip(), bold=(ri == 0))]])
        tbl.append(tr)
    return tbl

def strip_inline(t):
    return t

while i < n:
    line = lines[i]
    raw = line.rstrip("\n")
    s = raw.strip()

    # 注释：IMG 占位转成可回读锚点；普通注释跳过（含多行）
    if s.startswith("<!--"):
        m_img = re.match(r"^<!--\s*IMG:\s*(.*?)\s*-->$", s)
        if m_img:
            raw_meta = m_img.group(1).strip()
            parts = [p.strip() for p in raw_meta.split("|", 1)]
            marker = "〚IMG-%d〛" % len(images_md)
            images_md.append({
                "marker": marker,
                "name": parts[0] if parts and parts[0] else marker,
                "id": parts[1] if len(parts) > 1 and parts[1] else ""
            })
            blocks.append(["p", {"ind": {"hanging": 0, "left": body_ind(cur_heading_level)}}, leaf(marker)])
            # 同 TABLE 占位：前后留空行避免钉钉 markdown 合并到上一段
            if body_lines and body_lines[-1].strip():
                body_lines.append("")
            body_lines.append(marker)
            body_lines.append("")
            i += 1
            continue
        while i < n and "-->" not in lines[i]:
            i += 1
        i += 1
        continue
    if s == "" or s == "---":
        i += 1
        continue

    # 标题
    m = re.match(r"^(#{1,4})\s+(.*)$", s)
    if m:
        level = len(m.group(1))
        cur_heading_level = level
        blocks.append(heading_block(level, strip_inline(m.group(2)), numbered=True))
        body_lines.append(raw)
        i += 1
        continue

    # 表格（连续 | 行）—— jsonml 路径会把纯文字表降级成 columns，故不输出 table，
    # 改为输出占位段 + 把表格 markdown 存入 sidecar，由调用方写入后用 markdown 单独补。
    if s.startswith("|"):
        tbl_lines = []
        while i < n and lines[i].strip().startswith("|"):
            tbl_lines.append(lines[i].strip())
            i += 1
        marker = "〚TBL-%d〛" % len(tables_md)
        tables_md.append("\n".join(tbl_lines))
        # 占位段：ind 跟随当前标题正文档；文本是 marker，便于写入后定位替换
        blocks.append(["p", {"ind": {"hanging": 0, "left": body_ind(cur_heading_level)}}, leaf(marker)])
        # body.md 中，占位段前后强制留空行：避免钉钉 markdown 解析时把占位
        # 与上一个 list/段合并到同一 block（合并后无法用整段删除清理）
        if body_lines and body_lines[-1].strip():
            body_lines.append("")
        body_lines.append(marker)
        body_lines.append("")
        continue

    # 列表（- 或 两空格+-）
    m_li = re.match(r"^(\s*)-\s+(.*)$", raw)
    if m_li:
        indent = len(m_li.group(1))
        # 收集连续列表块，共享 listId
        listid = new_list_id()
        while i < n:
            ml = re.match(r"^(\s*)-\s+(.*)$", lines[i].rstrip("\n"))
            if not ml:
                break
            ind_sp = len(ml.group(1))
            lv = 0 if ind_sp < 2 else 1
            blocks.append(list_block(strip_inline(ml.group(2)), lv, listid, False, cur_heading_level))
            body_lines.append(lines[i].rstrip("\n"))
            i += 1
        continue

    # 普通段落
    blocks.append(para_block(strip_inline(s), cur_heading_level))
    body_lines.append(s)
    i += 1

root = ["root", {}] + blocks
json.dump(root, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
import os
# sidecar：表格 markdown（按 〚TBL-i〛 顺序），写入主体后用 markdown 单独补
side = os.path.splitext(OUT)[0] + ".tables.json"
json.dump(tables_md, open(side, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# sidecar：图片占位元数据（按 〚IMG-i〛 顺序），写入主体后定位并替换成左图右文表
img_side = os.path.splitext(OUT)[0] + ".images.json"
json.dump(images_md, open(img_side, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# 大文档 markdown 主体：保留 〚TBL〛/〚IMG〛 占位，供 markdown overwrite 后继续定位
body_side = os.path.splitext(OUT)[0] + ".body.md"
open(body_side, "w", encoding="utf-8").write("\n".join(body_lines) + "\n")
print("BLOCKS", len(blocks), "TABLES", len(tables_md), "IMAGES", len(images_md), "->", OUT, "+", side, "+", img_side, "+", body_side)
