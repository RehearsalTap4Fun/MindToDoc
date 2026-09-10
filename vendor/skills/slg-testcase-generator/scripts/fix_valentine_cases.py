#!/usr/bin/env python3
"""
修复情人节组队活动用例表格
- 扩展行数
- 重新写入所有用例数据
"""

import json
from pathlib import Path

def main():
    # 配置
    SPREADSHEET_ID = "1LsrAkUm1drGT7CKKfwtxsjO8srLUgWAraLxzJudoRnY"
    JSON_FILE = Path(__file__).parent.parent / "K1-testcase-config/output/valentine_team_testcases.json"
    
    # 初始化 Google API
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    
    token_file = Path(__file__).parent / 'token.json'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    sheets_service = build('sheets', 'v4', credentials=creds)
    print("✅ Google API 连接成功")
    
    # 读取用例数据
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)
    print(f"📖 共 {len(test_cases)} 条用例")
    
    START_ROW = 11
    required_rows = START_ROW + len(test_cases) + 20
    
    # 获取当前工作表信息
    print("\n📐 检查工作表...")
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_id = None
    current_rows = 0
    for sheet in sheet_metadata.get('sheets', []):
        if sheet['properties']['title'] == '用例':
            sheet_id = sheet['properties']['sheetId']
            current_rows = sheet['properties']['gridProperties']['rowCount']
            break
    
    print(f"   当前行数: {current_rows}")
    print(f"   需要行数: {required_rows}")
    
    # 扩展行数
    if current_rows < required_rows and sheet_id is not None:
        rows_to_add = required_rows - current_rows + 100
        print(f"\n➕ 添加 {rows_to_add} 行...")
        
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                'requests': [{
                    'appendDimension': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'length': rows_to_add
                    }
                }]
            }
        ).execute()
        print(f"   ✅ 行数已扩展")
    
    # 重新写入所有用例数据
    print("\n✍️ 重新写入用例数据...")
    BATCH_SIZE = 50
    
    for i in range(0, len(test_cases), BATCH_SIZE):
        batch = test_cases[i:i + BATCH_SIZE]
        start_row = START_ROW + i
        end_row = start_row + len(batch) - 1
        range_name = f"用例!A{start_row}:F{end_row}"
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body={'values': batch}
        ).execute()
        
        print(f"   写入行 {start_row}-{end_row}")
    
    # 重新合并单元格
    print("\n🔗 合并单元格...")
    
    def find_merge_ranges(data, col_index, start_row):
        merge_requests = []
        i = 0
        while i < len(data):
            current_value = data[i][col_index] if col_index < len(data[i]) else ""
            if not current_value:
                i += 1
                continue
            
            j = i + 1
            while j < len(data):
                next_value = data[j][col_index] if col_index < len(data[j]) else ""
                if next_value == "" or next_value is None:
                    j += 1
                else:
                    break
            
            if j - i > 1:
                merge_requests.append({
                    'mergeCells': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': start_row - 1 + i,
                            'endRowIndex': start_row - 1 + j,
                            'startColumnIndex': col_index,
                            'endColumnIndex': col_index + 1
                        },
                        'mergeType': 'MERGE_ALL'
                    }
                })
            i = j
        return merge_requests
    
    # 先取消现有合并
    try:
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                'requests': [{
                    'unmergeCells': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': START_ROW - 1,
                            'endRowIndex': START_ROW + len(test_cases),
                            'startColumnIndex': 1,
                            'endColumnIndex': 4
                        }
                    }
                }]
            }
        ).execute()
    except:
        pass
    
    all_merge_requests = []
    for col_idx in [1, 2, 3]:
        all_merge_requests.extend(find_merge_ranges(test_cases, col_idx, START_ROW))
    
    if all_merge_requests:
        for req in all_merge_requests:
            try:
                sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body={'requests': [req]}
                ).execute()
            except:
                pass
        print(f"   合并 {len(all_merge_requests)} 个区域")
    
    print("\n" + "=" * 60)
    print(f"🎉 修复完成！共 {len(test_cases)} 条测试用例")
    print(f"📎 链接: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print("=" * 60)

if __name__ == "__main__":
    main()
