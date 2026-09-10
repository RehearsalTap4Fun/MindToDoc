#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets 测试用例写入脚本（v2 - 原地增删改）

功能：
- 从 JSON 文件读取用例数据
- **原地写入**：先清除旧数据区域，再写入新数据，不留脏数据
- **手工修改保护**：写入前对比 Sheet 与本地 JSON，识别手工新增/修改行并警告
- 自动管理行数（多退少补）
- 分批写入用例数据
- 自动合并单元格

使用方法：
  python write_test_cases.py <spreadsheet_id> <json_file>
  python write_test_cases.py <spreadsheet_id> <json_file> --force   # 跳过手工修改检查

JSON 文件格式：二维数组 [["编号","模块","检查点","操作步骤","预期结果","备注"], ...]
"""

import os
import sys
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')

DATA_START_ROW = 11          # 用例数据起始行
BATCH_SIZE = 50              # 每批写入的行数
SHEET_NAME = '用例'          # 工作表名称


def get_credentials():
    """获取或刷新 Google API 凭证"""
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"错误：找不到 {CREDENTIALS_FILE}")
                print("请从 Google Cloud Console 下载 OAuth 2.0 客户端凭证")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def get_sheet_id(service, spreadsheet_id, sheet_name=SHEET_NAME):
    """获取工作表的 sheetId"""
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in spreadsheet.get('sheets', []):
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    raise ValueError(f"找不到名为 '{sheet_name}' 的工作表")


def validate_test_cases(test_cases):
    """验证并修复用例数据格式：每行6列，空值填充"""
    validated = []
    for i, row in enumerate(test_cases):
        if not isinstance(row, list):
            print(f"警告：第 {i+1} 行不是数组格式，已跳过")
            continue
        while len(row) < 6:
            row.append("")
        if len(row) > 6:
            row = row[:6]
        row = [str(v) if v is not None else "" for v in row]
        validated.append(row)
    return validated


def find_data_end_row(service, spreadsheet_id):
    """找到用例数据区域的实际结束行（第一个A列为空的行）"""
    range_name = f"{SHEET_NAME}!A{DATA_START_ROW}:A2000"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueRenderOption='FORMATTED_VALUE'
    ).execute()
    values = result.get('values', [])
    last_data = 0
    for i, row in enumerate(values):
        if row and row[0] and str(row[0]).strip():
            last_data = i
    return DATA_START_ROW + last_data if values else DATA_START_ROW - 1


def find_fixed_content_row(service, spreadsheet_id, search_start=11):
    """
    找到固定内容区域的起始行（用例数据下方的模板区域）。
    固定内容以「国服」等关键词开头，通常在 B 列。
    """
    range_name = f"{SHEET_NAME}!A{search_start}:B2000"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueRenderOption='FORMATTED_VALUE'
    ).execute()
    values = result.get('values', [])
    fixed_keywords = {'国服', '跨服', '合服兼容', '老版本', '异常', '用户体验', '音效',
                      '本地化', '画质', '文化局', '通用'}
    in_data = False
    for i, row in enumerate(values):
        actual_row = search_start + i
        a_val = row[0].strip() if row and len(row) > 0 and row[0] else ''
        b_val = row[1].strip() if row and len(row) > 1 and row[1] else ''
        if a_val and not in_data:
            in_data = True
        if in_data and not a_val and not b_val:
            continue
        if in_data and not a_val and b_val in fixed_keywords:
            return actual_row
    return None


def read_existing_data(service, spreadsheet_id, end_row):
    """读取 Sheet 当前用例数据区域"""
    range_name = f"{SHEET_NAME}!A{DATA_START_ROW}:F{end_row}"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueRenderOption='FORMATTED_VALUE'
    ).execute()
    values = result.get('values', [])
    normalized = []
    for row in values:
        while len(row) < 6:
            row.append('')
        normalized.append([str(v) if v else '' for v in row[:6]])
    return normalized


def detect_manual_edits(sheet_data, json_data):
    """
    对比 Sheet 现有数据与即将写入的 JSON 数据，找出手工修改。
    返回 (added_rows, modified_rows) 两个列表。
    """
    json_ids = {row[0] for row in json_data if row[0]}
    sheet_ids = {row[0] for row in sheet_data if row[0]}

    added = []
    for i, row in enumerate(sheet_data):
        if row[0] and row[0] not in json_ids:
            added.append((DATA_START_ROW + i, row))

    json_by_id = {row[0]: row for row in json_data if row[0]}
    modified = []
    for i, row in enumerate(sheet_data):
        rid = row[0]
        if rid and rid in json_by_id:
            j_row = json_by_id[rid]
            if row[3:6] != j_row[3:6]:
                modified.append((DATA_START_ROW + i, rid, row, j_row))

    return added, modified


def clear_data_range(service, spreadsheet_id, start_row, end_row):
    """清空指定行范围的 A-F 列数据"""
    if end_row < start_row:
        return
    range_name = f"{SHEET_NAME}!A{start_row}:F{end_row}"
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=range_name
    ).execute()


def adjust_rows(service, spreadsheet_id, sheet_id, current_data_end, new_data_end, fixed_row):
    """
    调整行数，保证数据区和固定内容区之间只有2行空隙。
    
    目标布局：[DATA_START_ROW ~ new_data_end] = 用例数据 | 2行空行 | 固定内容
    """
    GAP = 2

    if fixed_row is None:
        if new_data_end > current_data_end:
            need = new_data_end - current_data_end
            insert_pos = current_data_end + 1
            req = {'insertDimension': {'range': {
                'sheetId': sheet_id, 'dimension': 'ROWS',
                'startIndex': insert_pos - 1, 'endIndex': insert_pos - 1 + need
            }, 'inheritFromBefore': True}}
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body={'requests': [req]}
            ).execute()
            print(f"  插入 {need} 行")
        return

    target_fixed = new_data_end + 1 + GAP
    rows_between = fixed_row - new_data_end - 1

    if target_fixed < fixed_row:
        delete_count = fixed_row - target_fixed
        del_start = new_data_end + 1 + GAP
        req = {'deleteDimension': {'range': {
            'sheetId': sheet_id, 'dimension': 'ROWS',
            'startIndex': del_start - 1, 'endIndex': del_start - 1 + delete_count
        }}}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={'requests': [req]}
        ).execute()
        print(f"  删除 {delete_count} 行多余空行（固定内容从第{fixed_row}行上移到第{target_fixed}行）")
    elif target_fixed > fixed_row:
        insert_count = target_fixed - fixed_row
        req = {'insertDimension': {'range': {
            'sheetId': sheet_id, 'dimension': 'ROWS',
            'startIndex': fixed_row - 1, 'endIndex': fixed_row - 1 + insert_count
        }, 'inheritFromBefore': True}}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={'requests': [req]}
        ).execute()
        print(f"  在固定内容前插入 {insert_count} 行")
    else:
        print(f"  行数刚好，无需调整")


def write_data_batch(service, spreadsheet_id, data, start_row):
    """写入一批数据"""
    end_row = start_row + len(data) - 1
    range_name = f"{SHEET_NAME}!A{start_row}:F{end_row}"
    
    body = {
        'values': data
    }
    
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    
    return len(data)


def read_column_data(service, spreadsheet_id, column, start_row, end_row):
    """读取指定列的数据，用于合并单元格判断"""
    range_name = f"{SHEET_NAME}!{column}{start_row}:{column}{end_row}"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueRenderOption='FORMATTED_VALUE'  # 确保获取格式化后的值
    ).execute()
    
    values = result.get('values', [])
    
    # 处理每一行：空数组或空字符串都视为空
    data = []
    for row in values:
        if row and len(row) > 0 and row[0]:
            data.append(row[0])
        else:
            data.append('')
    
    # 补齐尾部缺失的行（API不返回尾部空行）
    expected_length = end_row - start_row + 1
    while len(data) < expected_length:
        data.append('')
    
    return data


def find_merge_ranges(data, column_index, start_row, sheet_id):
    """
    找出需要合并的单元格范围
    
    合并规则：
    - 有值的单元格与其下方连续的空单元格合并
    - 遇到下一个有值的单元格时停止合并
    - 单独一行（下面没有空行）不需要合并
    
    示例（data索引从0开始，实际行号从start_row开始）：
    data[0] = "入口"   → 行11，与下方空行合并（合并行11-13）
    data[1] = ""       → 行12
    data[2] = ""       → 行13
    data[3] = "界面"   → 行14，与下方空行合并（合并行14-15）
    data[4] = ""       → 行15
    data[5] = "按钮"   → 行16，不合并（下面紧跟有值或结束）
    """
    merge_requests = []
    
    if not data:
        return merge_requests
    
    # 跳过开头的空行
    i = 0
    while i < len(data) and not data[i]:
        i += 1
    
    while i < len(data):
        current_value = data[i]
        
        # 跳过空值（理论上不会进入这里，因为上面的逻辑保证 i 指向有值行）
        if not current_value:
            i += 1
            continue
        
        # 找到下一个有值的行
        j = i + 1
        while j < len(data) and not data[j]:
            j += 1
        
        # 如果 i 和 j 之间有空行（j > i + 1），则需要合并
        # Google Sheets API 的 endRowIndex 是 exclusive（不包含）
        # 所以合并 [i, j) 实际上是合并行 i 到 j-1
        if j - i > 1:
            merge_requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': start_row - 1 + i,
                        'endRowIndex': start_row - 1 + j,
                        'startColumnIndex': column_index,
                        'endColumnIndex': column_index + 1
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })
        
        i = j
    
    return merge_requests


def unmerge_cells(service, spreadsheet_id, sheet_id, start_row, end_row):
    """取消指定区域的所有合并单元格（逐个取消，避免范围冲突）"""
    # 先获取当前所有合并区域
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    all_merges = []
    for sheet in spreadsheet.get('sheets', []):
        if sheet['properties']['sheetId'] == sheet_id:
            all_merges = sheet.get('merges', [])
            break
    
    if not all_merges:
        print(f"  无合并区域需要取消")
        return
    
    # 筛选出B/C/D列（列索引1~3）且在数据行范围内的合并
    target_merges = []
    for merge in all_merges:
        col_start = merge.get('startColumnIndex', 0)
        col_end = merge.get('endColumnIndex', 0)
        row_start = merge.get('startRowIndex', 0)
        # 只处理B/C/D列且在数据区域内的合并
        if col_start >= 1 and col_end <= 4 and row_start >= start_row - 1:
            target_merges.append(merge)
    
    if not target_merges:
        print(f"  无B-D列合并区域需要取消")
        return
    
    # 逐个取消合并，避免范围冲突
    requests = [{'unmergeCells': {'range': merge}} for merge in target_merges]
    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
        print(f"  已取消 {len(requests)} 个B-D列合并区域（第 {start_row} 行起）")
    except Exception as e:
        print(f"  批量取消失败，尝试逐个取消: {e}")
        success = 0
        for req in requests:
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': [req]}
                ).execute()
                success += 1
            except:
                pass
        print(f"  逐个取消成功 {success}/{len(requests)}")


def merge_cells(service, spreadsheet_id, sheet_id, start_row, end_row):
    """执行单元格合并"""
    
    # 先取消现有的合并，避免冲突
    print("  步骤3.1：取消现有合并...")
    unmerge_cells(service, spreadsheet_id, sheet_id, start_row, end_row)
    
    columns_to_merge = [
        ('B', 1),  # B列 - 功能模块
        ('C', 2),  # C列 - 检查点
        ('D', 3),  # D列 - 操作步骤
    ]
    
    all_merge_requests = []
    
    print("  步骤3.2：计算合并区域...")
    for col_letter, col_index in columns_to_merge:
        data = read_column_data(service, spreadsheet_id, col_letter, start_row, end_row)
        # 调试：显示读取到的数据
        non_empty_count = sum(1 for d in data if d)
        print(f"    {col_letter}列：读取 {len(data)} 行，{non_empty_count} 个有值")
        
        merge_requests = find_merge_ranges(data, col_index, start_row, sheet_id)
        
        if merge_requests:
            print(f"    {col_letter}列：{len(merge_requests)} 个合并区域")
            all_merge_requests.extend(merge_requests)
    
    if all_merge_requests:
        print(f"  步骤3.3：执行合并...")
        body = {'requests': all_merge_requests}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        print(f"[OK] 成功合并 {len(all_merge_requests)} 个区域")
    else:
        print("  没有需要合并的单元格")


def write_test_cases(spreadsheet_id, test_cases, force=False):
    """
    v2 写入流程：原地增删改，不留脏数据，保护手工修改。

    流程：
    1. 读取 Sheet 现有数据，找到数据边界和固定内容位置
    2. 对比 JSON 与 Sheet，检测手工新增/修改行（--force 跳过）
    3. 取消旧合并
    4. 清空旧数据区域
    5. 调整行数（多删少插），保护固定内容
    6. 写入新数据
    7. 重新合并单元格
    """
    test_cases = validate_test_cases(test_cases)
    test_case_count = len(test_cases)
    if test_case_count == 0:
        print("错误：没有有效的用例数据")
        return False

    print(f"准备写入 {test_case_count} 条用例...")

    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)

    try:
        sheet_id = get_sheet_id(service, spreadsheet_id)

        # --- 步骤1：读取现有数据 ---
        print("步骤1：读取 Sheet 现有数据...")
        current_end = find_data_end_row(service, spreadsheet_id)
        fixed_row = find_fixed_content_row(service, spreadsheet_id, search_start=DATA_START_ROW)
        print(f"  当前数据区域：第{DATA_START_ROW}行 ~ 第{current_end}行（{current_end - DATA_START_ROW + 1}条）")
        if fixed_row:
            print(f"  固定内容起始行：第{fixed_row}行")
        else:
            print(f"  未检测到固定内容区域")

        # --- 步骤2：检测手工修改 ---
        if not force and current_end >= DATA_START_ROW:
            print("步骤2：检测手工修改...")
            sheet_data = read_existing_data(service, spreadsheet_id, current_end)
            added, modified = detect_manual_edits(sheet_data, test_cases)

            if added:
                print(f"\n  ⚠️  检测到 {len(added)} 条 Sheet 上存在但 JSON 中没有的行（可能是手工新增）：")
                for row_num, row in added:
                    print(f"    第{row_num}行: [{row[0]}] {row[3][:40]}...")
                print(f"  这些行将在本次写入中被覆盖。如需保留，请先将它们加入 JSON 文件。")
                print(f"  使用 --force 跳过此检查。\n")

            if modified:
                print(f"  ⚠️  检测到 {len(modified)} 条 Sheet 上内容与 JSON 不同的行（可能是手工修改）：")
                for row_num, rid, s_row, j_row in modified[:5]:
                    print(f"    {rid}: Sheet=[{s_row[3][:30]}] vs JSON=[{j_row[3][:30]}]")
                if len(modified) > 5:
                    print(f"    ... 及其他 {len(modified)-5} 条")
        else:
            print("步骤2：跳过手工修改检测（--force 模式或无现有数据）")

        # --- 步骤3：取消旧合并 ---
        print("步骤3：取消旧合并区域...")
        scan_end = max(current_end, DATA_START_ROW + test_case_count) + 50
        unmerge_cells(service, spreadsheet_id, sheet_id, DATA_START_ROW, scan_end)

        # --- 步骤4：清空旧数据区域 ---
        print("步骤4：清空旧数据区域...")
        clear_data_range(service, spreadsheet_id, DATA_START_ROW, current_end)
        print(f"  已清空第{DATA_START_ROW}行 ~ 第{current_end}行")

        # --- 步骤5：调整行数（清除多余空行或插入不足的行） ---
        new_end = DATA_START_ROW + test_case_count - 1
        needs_adjust = (new_end != current_end)
        if fixed_row and (fixed_row - new_end - 1) > 2:
            needs_adjust = True
        if needs_adjust:
            print("步骤5：调整行数...")
            adjust_rows(service, spreadsheet_id, sheet_id, current_end, new_end, fixed_row)
        else:
            print("步骤5：行数无需调整")

        # --- 步骤6：分批写入 ---
        print(f"步骤6：分批写入用例数据...")
        total_written = 0
        batch_num = 0
        for i in range(0, test_case_count, BATCH_SIZE):
            batch = test_cases[i:i + BATCH_SIZE]
            start_row = DATA_START_ROW + i
            written = write_data_batch(service, spreadsheet_id, batch, start_row)
            total_written += written
            batch_num += 1
            end_row = start_row + len(batch) - 1
            print(f"  第 {batch_num} 批：A{start_row}:F{end_row}（{len(batch)} 行）")
        print(f"[OK] 共写入 {total_written} 条用例")

        # --- 步骤7：合并单元格 ---
        print("步骤7：合并单元格...")
        merge_end = DATA_START_ROW + test_case_count - 1
        merge_cells(service, spreadsheet_id, sheet_id, DATA_START_ROW, merge_end)

        print("\n[OK] 用例写入完成！（原地更新，无脏数据）")
        return True

    except HttpError as error:
        print(f"API 错误：{error}")
        return False


def load_test_cases_from_json(json_file):
    """从 JSON 文件加载用例数据"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 支持两种格式
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and 'test_cases' in data:
        return data['test_cases']
    else:
        raise ValueError("JSON 格式不正确，应为数组或包含 'test_cases' 键的对象")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = [a for a in sys.argv[1:] if a.startswith('--')]
    force = '--force' in flags

    if len(args) < 2:
        print("用法：python write_test_cases.py <spreadsheet_id> <json_file> [--force]")
        print()
        print("参数：")
        print("  spreadsheet_id  Google Sheets 文件 ID")
        print("  json_file       包含用例数据的 JSON 文件路径")
        print("  --force         跳过手工修改检测，直接覆盖写入")
        print()
        print("v2 特性：")
        print("  - 原地更新：清除旧数据后写入，不留脏数据")
        print("  - 手工修改保护：写入前对比 Sheet 与 JSON，警告手工新增/修改行")
        print("  - 智能行管理：多退少补，保护固定内容区域")
        sys.exit(1)

    spreadsheet_id = args[0]
    json_file = args[1]

    if not os.path.exists(json_file):
        print(f"错误：找不到文件 {json_file}")
        sys.exit(1)

    try:
        test_cases = load_test_cases_from_json(json_file)
        print(f"从 {json_file} 加载了 {len(test_cases)} 条用例")

        success = write_test_cases(spreadsheet_id, test_cases, force=force)
        sys.exit(0 if success else 1)

    except json.JSONDecodeError as e:
        print(f"JSON 解析错误：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
