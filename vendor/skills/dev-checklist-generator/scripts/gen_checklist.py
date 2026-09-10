# -*- coding: utf-8 -*-
"""
开发 Checklist Excel 生成脚本模板

使用方法：
1. 修改 TASKS 列表为实际任务数据
2. 修改 OUTPUT_FILENAME 为目标文件名
3. 修改 OUTPUT_DIR 为目标目录
4. 运行: python gen_checklist.py

TASKS 格式: (模块名, 子模块名, 任务描述, 职能, 优先级, 备注)
- 模块行:   ('一、模块名', None, None, None, None, None)
- 子模块行: (None, '1.1 子模块名', None, None, None, None)
- 任务行:   (None, None, '任务描述', '职能', 'P0', '备注')

职能可选值: '数值策划', 'UI', '原画&3D', '客户端', '服务器'
优先级可选值: 'P0', 'P1', 'P2'
"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ═══════════════════════════════════════════
# 配置区 - 修改以下内容
# ═══════════════════════════════════════════

OUTPUT_DIR = r'.'  # 输出目录
OUTPUT_FILENAME = '开发checklist.xlsx'  # 输出文件名

# 职能列表与颜色（可自定义）
ROLES = ['数值策划', 'UI', '原画&3D', '客户端', '服务器']
ROLE_COLORS = {
    '数值策划': 'FFF2CC',  # 黄
    'UI': 'E2EFDA',        # 绿
    '原画&3D': 'FCE4EC',   # 粉
    '客户端': 'DAEEF3',    # 青
    '服务器': 'E8DAEF',    # 紫
}

# ═══════════════════════════════════════════
# 任务数据 - 替换为实际内容
# ═══════════════════════════════════════════

TASKS = [
    # 示例数据（替换为实际任务）
    ('一、示例模块', None, None, None, None, None),
    (None, '1.1 示例子模块', None, None, None, None),
    (None, None, '示例任务描述', '客户端', 'P0', '示例备注'),
    (None, None, '示例配置任务', '数值策划', 'P0', ''),
    (None, None, '示例UI任务', 'UI', 'P1', ''),
    (None, None, '示例接口任务', '服务器', 'P0', ''),
    (None, None, '示例美术任务', '原画&3D', 'P1', ''),
]

# ═══════════════════════════════════════════
# 以下为生成逻辑，通常无需修改
# ═══════════════════════════════════════════

THIN = Side(style='thin', color='AAAAAA')
BORDER = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
HEADER_FONT = Font(bold=True, size=12, color='FFFFFF')
HEADER_FILL = PatternFill('solid', fgColor='4472C4')
HEADER_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)
MODULE_FONT = Font(bold=True, size=11, color='FFFFFF')
MODULE_FILL = PatternFill('solid', fgColor='5B9BD5')
MODULE_ALIGN = Alignment(horizontal='left', vertical='center')
SUB_FONT = Font(bold=True, size=10, color='305496')
SUB_FILL = PatternFill('solid', fgColor='D6E4F0')
SUB_ALIGN = Alignment(horizontal='left', vertical='center')
CELL_ALIGN = Alignment(horizontal='left', vertical='center', wrap_text=True)
CENTER_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)
ROLE_FILLS = {k: PatternFill('solid', fgColor=v) for k, v in ROLE_COLORS.items()}


def apply_border(ws, row, col_start, col_end):
    for ci in range(col_start, col_end + 1):
        ws.cell(row=row, column=ci).border = BORDER


def create_header(ws, headers, widths):
    for ci, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(ci)].width = w


def build_main_sheet(wb):
    ws = wb.active
    ws.title = '总表'
    headers = ['序号', '模块', '子模块', '任务描述', '职能', '优先级', '状态', '备注']
    widths = [6, 18, 20, 55, 10, 8, 8, 30]
    create_header(ws, headers, widths)
    num_cols = len(headers)

    ws.auto_filter.ref = f'A1:{get_column_letter(num_cols)}1'
    ws.freeze_panes = 'A2'

    row = 2
    idx = 0
    cur_module = ''
    cur_sub = ''

    for module, sub, task, role, priority, note in TASKS:
        if module is not None and sub is None and task is None:
            cur_module = module
            cur_sub = ''
            for ci in range(1, num_cols + 1):
                cell = ws.cell(row=row, column=ci)
                cell.fill = MODULE_FILL
                cell.font = MODULE_FONT
                cell.alignment = MODULE_ALIGN
                cell.border = BORDER
            ws.cell(row=row, column=2, value=module)
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=num_cols)
            row += 1
            continue

        if sub is not None and task is None:
            cur_sub = sub
            for ci in range(1, num_cols + 1):
                cell = ws.cell(row=row, column=ci)
                cell.fill = SUB_FILL
                cell.font = SUB_FONT
                cell.alignment = SUB_ALIGN
                cell.border = BORDER
            ws.cell(row=row, column=3, value=sub)
            ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=num_cols)
            row += 1
            continue

        idx += 1
        ws.cell(row=row, column=1, value=idx).alignment = CENTER_ALIGN
        ws.cell(row=row, column=2, value=cur_module).alignment = CELL_ALIGN
        ws.cell(row=row, column=3, value=cur_sub).alignment = CELL_ALIGN
        ws.cell(row=row, column=4, value=task).alignment = CELL_ALIGN
        role_cell = ws.cell(row=row, column=5, value=role)
        role_cell.alignment = CENTER_ALIGN
        if role in ROLE_FILLS:
            role_cell.fill = ROLE_FILLS[role]
        ws.cell(row=row, column=6, value=priority).alignment = CENTER_ALIGN
        ws.cell(row=row, column=7, value='待开始').alignment = CENTER_ALIGN
        ws.cell(row=row, column=8, value=note).alignment = CELL_ALIGN
        apply_border(ws, row, 1, num_cols)
        row += 1

    return ws


def build_role_sheet(wb, role_name):
    ws = wb.create_sheet(title=role_name)
    role_tasks = [(m, s, t, r, p, n) for m, s, t, r, p, n in TASKS if r == role_name]
    headers = ['序号', '模块', '子模块', '任务描述', '优先级', '状态', '备注']
    widths = [6, 18, 20, 58, 8, 8, 30]
    create_header(ws, headers, widths)
    num_cols = len(headers)

    ws.auto_filter.ref = f'A1:{get_column_letter(num_cols)}1'
    ws.freeze_panes = 'A2'

    r = 2
    for i, (m, s, t, role, p, n) in enumerate(role_tasks, 1):
        ws.cell(row=r, column=1, value=i).alignment = CENTER_ALIGN
        ws.cell(row=r, column=2, value=m).alignment = CELL_ALIGN
        ws.cell(row=r, column=3, value=s).alignment = CELL_ALIGN
        c4 = ws.cell(row=r, column=4, value=t)
        c4.alignment = CELL_ALIGN
        c4.fill = ROLE_FILLS.get(role_name, PatternFill())
        ws.cell(row=r, column=5, value=p).alignment = CENTER_ALIGN
        ws.cell(row=r, column=6, value='待开始').alignment = CENTER_ALIGN
        ws.cell(row=r, column=7, value=n).alignment = CELL_ALIGN
        apply_border(ws, r, 1, num_cols)
        r += 1

    # 底部统计
    r += 1
    ws.cell(row=r, column=1, value='统计').font = Font(bold=True, size=11)
    ws.cell(row=r, column=2, value=f'任务总数: {len(role_tasks)}').font = Font(bold=True)
    p0 = sum(1 for _, _, _, _, p, _ in role_tasks if p == 'P0')
    p1 = sum(1 for _, _, _, _, p, _ in role_tasks if p == 'P1')
    p2 = sum(1 for _, _, _, _, p, _ in role_tasks if p == 'P2')
    ws.cell(row=r, column=3, value=f'P0: {p0}').font = Font(bold=True, color='FF0000')
    ws.cell(row=r, column=4, value=f'P1: {p1}').font = Font(bold=True, color='FF8C00')
    ws.cell(row=r, column=5, value=f'P2: {p2}').font = Font(bold=True, color='008000')
    return ws


def build_stats_sheet(wb):
    ws = wb.create_sheet(title='统计总览', index=1)
    headers = ['职能', '任务总数', 'P0', 'P1', 'P2']
    widths = [12, 10, 8, 8, 8]
    create_header(ws, headers, widths)

    for ri, rn in enumerate(ROLES, 2):
        rt = [t for t in TASKS if t[3] == rn]
        c1 = ws.cell(row=ri, column=1, value=rn)
        c1.alignment = CENTER_ALIGN
        c1.fill = ROLE_FILLS.get(rn, PatternFill())
        c1.font = Font(bold=True, size=11)
        ws.cell(row=ri, column=2, value=len(rt)).alignment = CENTER_ALIGN
        ws.cell(row=ri, column=3, value=sum(1 for t in rt if t[4] == 'P0')).alignment = CENTER_ALIGN
        ws.cell(row=ri, column=4, value=sum(1 for t in rt if t[4] == 'P1')).alignment = CENTER_ALIGN
        ws.cell(row=ri, column=5, value=sum(1 for t in rt if t[4] == 'P2')).alignment = CENTER_ALIGN
        for ci in range(1, 6):
            ws.cell(row=ri, column=ci).border = BORDER
            ws.cell(row=ri, column=ci).font = Font(bold=True, size=11)

    tr = len(ROLES) + 2
    ws.cell(row=tr, column=1, value='合计').alignment = CENTER_ALIGN
    ws.cell(row=tr, column=1).font = Font(bold=True, size=11)
    ws.cell(row=tr, column=1).border = BORDER
    for ci in range(2, 6):
        c = get_column_letter(ci)
        ws.cell(row=tr, column=ci, value=f'=SUM({c}2:{c}{tr - 1})')
        ws.cell(row=tr, column=ci).alignment = CENTER_ALIGN
        ws.cell(row=tr, column=ci).font = Font(bold=True, size=11)
        ws.cell(row=tr, column=ci).border = BORDER
    return ws


def main():
    wb = Workbook()
    build_main_sheet(wb)
    build_stats_sheet(wb)
    for role_name in ROLES:
        build_role_sheet(wb, role_name)

    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    wb.save(output_path)
    print(f'OK: {output_path}')


if __name__ == '__main__':
    main()
