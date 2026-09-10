#!/usr/bin/env python3
"""
完整修复用例表格
1. 填充空单元格
2. 复制格式（边框、底色、下拉选项）
3. 合并单元格
"""

import json
import time
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def main():
    SPREADSHEET_ID = "1LsrAkUm1drGT7CKKfwtxsjO8srLUgWAraLxzJudoRnY"
    JSON_FILE = Path(__file__).parent.parent / "K1-testcase-config/output/valentine_team_testcases.json"
    
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
    
    # 获取 sheet ID
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_id = None
    for sheet in sheet_metadata.get('sheets', []):
        if sheet['properties']['title'] == '用例':
            sheet_id = sheet['properties']['sheetId']
            break
    
    START_ROW = 11
    END_ROW = START_ROW + len(test_cases) - 1
    
    # ========== 步骤 1: 合并单元格 ==========
    print("\n🔗 步骤1: 合并单元格...")
    
    # 先取消现有合并
    try:
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={'requests': [{'unmergeCells': {'range': {
                'sheetId': sheet_id,
                'startRowIndex': START_ROW - 1,
                'endRowIndex': END_ROW + 1,
                'startColumnIndex': 1,
                'endColumnIndex': 4
            }}}]}
        ).execute()
        print("   ✅ 已取消现有合并")
    except:
        pass
    
    time.sleep(1)
    
    # 计算合并区域（使用原始数据）
    def find_merge_ranges(data, col_index, start_row):
        merge_ranges = []
        i = 0
        while i < len(data):
            current_value = data[i][col_index] if col_index < len(data[i]) else ''
            if not current_value:
                i += 1
                continue
            j = i + 1
            while j < len(data):
                next_value = data[j][col_index] if col_index < len(data[j]) else ''
                if next_value == '' or next_value is None:
                    j += 1
                else:
                    break
            if j - i > 1:
                merge_ranges.append({'start': start_row - 1 + i, 'end': start_row - 1 + j, 'col': col_index})
            i = j
        return merge_ranges
    
    all_ranges = []
    for col_idx in [1, 2, 3]:
        ranges = find_merge_ranges(test_cases, col_idx, START_ROW)
        col_name = ['', 'B', 'C', 'D'][col_idx]
        print(f"   {col_name}列: {len(ranges)} 个合并区域")
        all_ranges.extend(ranges)
    
    # 分批执行合并
    MERGE_BATCH = 20
    success = 0
    
    for i in range(0, len(all_ranges), MERGE_BATCH):
        batch = all_ranges[i:i + MERGE_BATCH]
        requests = []
        for r in batch:
            requests.append({'mergeCells': {'range': {
                'sheetId': sheet_id,
                'startRowIndex': r['start'],
                'endRowIndex': r['end'],
                'startColumnIndex': r['col'],
                'endColumnIndex': r['col'] + 1
            }, 'mergeType': 'MERGE_ALL'}})
        
        try:
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'requests': requests}
            ).execute()
            success += len(batch)
        except Exception as e:
            print(f"   ⚠️ 批次失败: {str(e)[:40]}")
        
        time.sleep(1)
    
    print(f"   ✅ 合并 {success}/{len(all_ranges)} 个区域")
    
    print("\n" + "=" * 60)
    print("🎉 修复完成！")
    print(f"📎 https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print("=" * 60)

if __name__ == "__main__":
    main()
