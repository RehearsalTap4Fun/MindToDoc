#!/usr/bin/env python3
"""
生成 K1 / X15 音效需求拆分与验收文档 (xlsx)
用法: python3 generate_sound_doc.py <output_path> <json_data_path>

json_data 格式:
{
  "project": "X15",
  "sheets": [
    {
      "name": "Sheet名称",
      "note": "Overview 备注",
      "rows": [
        {"type": "module", "name": "模块标题"},
        {"type": "submod", "name": "子模块标题"},
        {
          "t": "2D|3D",
          "event": "ui_xxx",                  # 事件名
          "asset": "common_btn_click",        # 音效资源名（去 Wwise）
          "tag": "复用|新增|沿用X1",            # 标注
          "desc": "音效描述（新增必填，复用可空）",
          "prompt": "时长|氛围|音色|动态|处理",  # 生成提示词（新增必填）
          "bank": "Soundbank名",
          "trigger": "触发时机",
          "priority": "P0|P1|P2"
        }
      ]
    }
  ]
}
"""
import sys, json
from pathlib import Path
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

COLOR_HEADER = "4472C4"
COLOR_MODULE = "D9E1F2"
COLOR_SUBMOD = "E2EFDA"
COLOR_REUSE  = "FFF2CC"  # 复用：浅黄
COLOR_NEW    = "FCE4D6"  # 新增：浅橙
COLOR_X1     = "E7E6E6"  # 沿用X1：浅灰

TAG_FILL = {
    "复用": COLOR_REUSE,
    "新增": COLOR_NEW,
    "沿用X1": COLOR_X1,
}

def hfont(bold=True, color="FFFFFF"):
    return Font(bold=bold, color=color, name="微软雅黑", size=10)

def cfont(bold=False):
    return Font(bold=bold, name="微软雅黑", size=10)

def hfill(hex_c):
    return PatternFill("solid", fgColor=hex_c)

def tborder():
    s = Side(style="thin", color="BBBBBB")
    return Border(left=s, right=s, top=s, bottom=s)

def walign(h="left"):
    return Alignment(wrap_text=True, vertical="center", horizontal=h)

# 需求审核列：程序触发、资源生产、制作说明和验收状态必须在同一行可见。
COLS = [
    "Type",
    "Event Name 事件名称",
    "标注",
    "音效资源名 Asset",
    "Description 描述",
    "Prompt 制作方向",
    "Soundbank 资源包",
    "触发时机",
    "优先级",
    "是否循环",
    "需 StopEvent",
    "策划验收",
    "音效验收",
]
WIDTHS = [6, 38, 8, 30, 34, 44, 18, 34, 8, 10, 12, 10, 10]

def make_sheet(ws, rows, k1=False):
    columns = COLS + (["复用依据／备注", "停止条件"] if k1 else [])
    widths = WIDTHS + ([48, 38] if k1 else [])
    for ci, (col, w) in enumerate(zip(columns, widths), 1):
        c = ws.cell(row=1, column=ci, value=col)
        c.font = hfont(); c.fill = hfill(COLOR_HEADER)
        c.alignment = walign("center"); c.border = tborder()
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.row_dimensions[1].height = 22

    ri = 2
    for item in rows:
        if item.get("type") == "module":
            ws.merge_cells(start_row=ri, start_column=1, end_row=ri, end_column=len(columns))
            c = ws.cell(row=ri, column=1, value=item["name"])
            c.font = Font(bold=True, name="微软雅黑", size=10, color="1F3864")
            c.fill = hfill(COLOR_MODULE); c.alignment = walign(); c.border = tborder()
            ws.row_dimensions[ri].height = 18
        elif item.get("type") == "submod":
            ws.merge_cells(start_row=ri, start_column=1, end_row=ri, end_column=len(columns))
            c = ws.cell(row=ri, column=1, value=item["name"])
            c.font = Font(bold=True, name="微软雅黑", size=10, color="375623")
            c.fill = hfill(COLOR_SUBMOD); c.alignment = walign(); c.border = tborder()
            ws.row_dimensions[ri].height = 16
        else:
            tag = item.get("tag", "新增")
            vals = [
                item.get("t", "2D"),
                item.get("event", ""),
                tag,
                item.get("asset", ""),
                item.get("desc", ""),
                item.get("prompt", item.get("prompt_en", "")),
                item.get("bank", ""),
                item.get("trigger", ""),
                item.get("priority", "P1"),
                item.get("loop", "FALSE"),
                item.get("stop_event_needed", "FALSE"),
                "", "",
            ]
            if k1:
                vals.extend([item.get("notes", ""), item.get("stop_condition", "")])
            for ci, v in enumerate(vals, 1):
                c = ws.cell(row=ri, column=ci, value=v)
                c.font = cfont(); c.alignment = walign(); c.border = tborder()
            # 给"标注"列上色，整行也染一层底色突出
            tag_color = TAG_FILL.get(tag)
            if tag_color:
                ws.cell(row=ri, column=3).fill = hfill(tag_color)
            ws.row_dimensions[ri].height = 32
        ri += 1
    ws.freeze_panes = "B2"

def validate_k1_demand(data):
    sheets = data.get("sheets", [])
    if not sheets:
        raise ValueError("K1 demand requires at least one sheet with a source note")
    sheet_names = {"程序策划注意事项".casefold(), "overview"}
    for sheet in sheets:
        name = sheet.get("name", "")
        if (not name or len(name) > 31 or any(c in name for c in '[]:*?/\\')
                or name.casefold() in sheet_names):
            raise ValueError(f"invalid or duplicate demand sheet name: {name}")
        sheet_names.add(name.casefold())
        if not str(sheet.get("note") or "").strip():
            raise ValueError(f"K1 demand requires source/review evidence: {name}")
        if not isinstance(sheet.get("rows"), list):
            raise ValueError(f"K1 demand rows must be a list: {name}")
        events = set()
        for row in sheet["rows"]:
            if row.get("type") in {"module", "submod"}:
                continue
            for field in ("event", "tag", "asset", "trigger", "priority", "loop", "stop_event_needed"):
                if field not in row or row[field] is None or str(row[field]).strip() == "":
                    raise ValueError(f"K1 demand missing {field}: {name}")
            if row["event"] in events:
                raise ValueError(f"duplicate event: {row['event']}")
            events.add(row["event"])
            if row["tag"] not in TAG_FILL or row["priority"] not in {"P0", "P1", "P2"}:
                raise ValueError(f"invalid tag/priority: {row['event']}")
            for field in ("loop", "stop_event_needed"):
                if str(row[field]).upper() not in {"TRUE", "FALSE"}:
                    raise ValueError(f"invalid {field}: {row['event']}")
            if row["tag"] == "新增" and not str(row.get("desc") or "").strip():
                raise ValueError(f"new sound requires desc: {row['event']}")
            if row["tag"] != "新增" and not str(row.get("notes") or "").strip():
                raise ValueError(f"reuse requires evidence in notes: {row['event']}")
            if str(row["loop"]).upper() == "TRUE" and (
                str(row["stop_event_needed"]).upper() != "TRUE"
                or not str(row.get("stop_condition") or "").strip()
            ):
                raise ValueError(f"loop requires explicit stop condition: {row['event']}")


def build(data, out_path):
    k1 = str(data.get("project", "")).upper() == "K1"
    if k1:
        validate_k1_demand(data)
    wb = openpyxl.Workbook()

    # 注意事项 sheet
    ws0 = wb.active
    ws0.title = "程序策划注意事项"
    ws0.column_dimensions["A"].width = 110
    note = (
        "【X15 音效系统说明】\n\n"
        "1. X15 不再使用 Wwise 中间层。事件名（Event）不带 Play_/Stop_ 前缀：\n"
        "   - 事件名：程序调用接口用，如 ui_mainline_chest_claim；\n"
        "   - 程序通过调用不同接口（PlayEvent / StopEvent）来区分播放和停止；\n"
        "   - 循环音效用 _loop 后缀标识，程序调 StopEvent 停止。\n\n"
        "2. 事件名与音效资源名（Asset）分离：\n"
        "   - 事件名是触发时机的标识，资源名是实际音频文件名；\n"
        "   - 多个事件可以指向同一个资源（复用）。\n\n"
        "3. 音效统一通过客户端管理类 GameAudio 调用。\n\n"
        "4. 真实复用优先：只有 audio/<资源名>.ogg 已存在时才能标复用；\n"
        "   没有真实 OGG 的 common_xxx 必须按新增制作，不能模拟复用。\n\n"
        "5. 标注说明：\n"
        "   - 复用（黄）：只能直接用已存在的 audio/<资源名>.ogg；\n"
        "   - 新增（橙）：需要按提示词制作新资源；\n"
        "   - 沿用X1（灰）：使用 X1 已有资源。\n\n"
        f"项目：{data.get('project', '')}\n"
        f"模块：{', '.join(s['name'] for s in data.get('sheets', []))}"
    )
    if k1:
        note = (
            "【K1 音效需求说明】\n\n"
            "本文件仅用于需求审核，不表示资源已制作或已接入客户端。\n"
            "复用项以已核验的 AudioList ID 或文件名及备注中的来源为依据。\n"
            "新增资源名和业务事件标识可为拟定名称，工程映射另行确认。\n"
            "循环声音须明确停止条件。零需求结论及核查依据见 Overview。\n"
            "状态：需求文档已生成，待策划审核。"
        )
    c = ws0.cell(row=1, column=1, value=note)
    c.font = Font(name="微软雅黑", size=10)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws0.row_dimensions[1].height = 320

    total = 0
    new_total = 0
    reuse_total = 0
    x1_total = 0
    ov_rows = []
    for sheet in data.get("sheets", []):
        ws = wb.create_sheet(sheet["name"])
        make_sheet(ws, sheet["rows"], k1=k1)
        cnt = 0
        s_new = s_reuse = s_x1 = 0
        for r in sheet["rows"]:
            if r.get("type") in ("module", "submod"):
                continue
            cnt += 1
            tag = r.get("tag", "新增")
            if tag == "新增":
                s_new += 1
            elif tag == "复用":
                s_reuse += 1
            elif tag == "沿用X1":
                s_x1 += 1
        total += cnt
        new_total += s_new
        reuse_total += s_reuse
        x1_total += s_x1
        ov_rows.append((sheet["name"], cnt, s_new, s_reuse, s_x1, sheet.get("note", "")))

    # Overview
    ws_ov = wb.create_sheet("Overview")
    ov_cols = ["模块", "音效总数", "新增", "复用", "沿用X1", "说明"]
    ov_widths = [22, 10, 8, 8, 10, 50]
    for ci, (h, w) in enumerate(zip(ov_cols, ov_widths), 1):
        ws_ov.column_dimensions[get_column_letter(ci)].width = w
        c = ws_ov.cell(row=1, column=ci, value=h)
        c.font = hfont(); c.fill = hfill(COLOR_HEADER)
        c.alignment = walign("center"); c.border = tborder()

    for ri, (mod, cnt, s_new, s_reuse, s_x1, note) in enumerate(ov_rows, 2):
        for ci, v in enumerate([mod, cnt, s_new, s_reuse, s_x1, note], 1):
            c = ws_ov.cell(row=ri, column=ci, value=v)
            c.font = cfont(); c.alignment = walign(); c.border = tborder()

    # 合计行
    ri = len(ov_rows) + 2
    for ci, v in enumerate(["合计", total, new_total, reuse_total, x1_total, ""], 1):
        c = ws_ov.cell(row=ri, column=ci, value=v)
        c.font = cfont(bold=True); c.alignment = walign(); c.border = tborder()

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"Saved: {out_path}")
    print(f"  共 {total} 条 — 新增 {new_total} / 复用 {reuse_total} / 沿用X1 {x1_total}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: generate_sound_doc.py <output.xlsx> <data.json>")
        sys.exit(1)
    with open(sys.argv[2], encoding="utf-8") as f:
        data = json.load(f)
    build(data, sys.argv[1])
