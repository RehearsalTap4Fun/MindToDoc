# -*- coding: utf-8 -*-
"""按项目组四列表模板生成 BI 日志需求 Excel（前两列纵向合并）。

用法：在 Python 中构造 groups 后直接调用 write_workbook，勿经 JSON 中转。

    from pathlib import Path
    from gen_bi_requirements_excel import write_workbook

    write_workbook(
        Path("输出路径.xlsx"),
        groups=[
            {
                "trigger": "玩家探索关卡战斗胜利、服务器发放关卡奖励时",
                "table": "user_asset",
                "fields": [
                    ["asset_id", "道具/货币 ID"],
                    ["reason_id", "dragon_breed_explore_reward（新增）"],
                ],
            },
        ],
    )
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
except ImportError:
    print("需要 openpyxl: pip install openpyxl", file=sys.stderr)
    sys.exit(1)

thin = Side(style="thin", color="CCCCCC")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top", horizontal="left")
HEADER_FONT = Font(bold=True)

HEADERS = ("日志触发逻辑", "日志表名/类型", "字段名", "字段含义/取值")


def write_workbook(
    output: Path,
    groups: list[dict],
    sheet_name: str = "BI日志需求",
) -> None:
    """将 groups 写入四列表 Excel。

    groups 每项结构：
        trigger: 日志触发逻辑（何时/何条件下记录）
        table: 日志表名/类型
        fields: [[字段名, 字段含义/取值], ...]

    trigger 也可用已废弃的 desc 键（兼容旧数据）。
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]

    for col, h in enumerate(HEADERS, start=1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = HEADER_FONT
        c.border = BORDER
        c.alignment = WRAP

    row = 2
    for g in groups:
        trigger = g.get("trigger") or g["desc"]
        table = g["table"]
        fields = g["fields"]
        start = row
        for fname, fdef in fields:
            ws.cell(row=row, column=1, value=trigger)
            ws.cell(row=row, column=2, value=table)
            ws.cell(row=row, column=3, value=fname)
            ws.cell(row=row, column=4, value=fdef)
            for c in range(1, 5):
                cell = ws.cell(row=row, column=c)
                cell.border = BORDER
                cell.alignment = WRAP
            row += 1
        end = row - 1
        if end > start:
            ws.merge_cells(start_row=start, start_column=1, end_row=end, end_column=1)
            ws.merge_cells(start_row=start, start_column=2, end_row=end, end_column=2)

    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 62

    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)
    print(f"已生成: {output}")
