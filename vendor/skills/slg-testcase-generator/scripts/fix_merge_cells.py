#!/usr/bin/env python3
"""
修复单元格合并问题
- 先取消所有现有合并
- 重新计算并批量执行合并
"""

import json
from pathlib import Path

def main():
    SPREADSHEET_ID = "1LsrAkUm1drGT7CKKfwtxsjO8srLUgWAraLxzJudoRnY"
    JSON_FILE = Path(__file__).parent.parent / "K1-testcase-config/output/valentine_team_testcases.json"
    
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
    
    # 获取 sheet ID
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_id = None
    for sheet in sheet_metadata.get('sheets', []):
        if sheet['properties']['title'] == '用例':
            sheet_id = sheet['properties']['sheetId']
            break
    
    if sheet_id is None:
        print("❌ 未找到 '用例' 工作表")
        return
    
    print(f"   Sheet ID: {sheet_id}")
    
    # 1. 取消现有的所有合并
    print("\n🔓 取消现有合并...")
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
                            'startColumnIndex': 1,  # B 列
                            'endColumnIndex': 4     # 到 D 列
                        }
                    }
                }]
            }
        ).execute()
        print("   ✅ 已取消现有合并")
    except Exception as e:
        print(f"   ⚠️ 取消合并时出错: {e}")
    
    # 2. 计算所有需要合并的区域
    print("\n📐 计算合并区域...")
    
    def find_merge_ranges(data, col_index, start_row):
        """找出需要合并的单元格范围"""
        merge_ranges = []
        i = 0
        while i < len(data):
            # 获取当前值
            current_value = data[i][col_index] if col_index < len(data[i]) else ""
            
            # 跳过空值行（它们会被合并到上面）
            if not current_value:
                i += 1
                continue
            
            # 找到下一个有值的行
            j = i + 1
            while j < len(data):
                next_value = data[j][col_index] if col_index < len(data[j]) else ""
                if next_value == "" or next_value is None:
                    j += 1
                else:
                    break
            
            # 如果有多行需要合并
            if j - i > 1:
                # Google Sheets 行索引是 0-based
                merge_ranges.append({
                    'start_row': start_row - 1 + i,  # 转为 0-based
                    'end_row': start_row - 1 + j,    # exclusive
                    'col': col_index,
                    'value': current_value[:20] + '...' if len(current_value) > 20 else current_value
                })
            
            i = j
        
        return merge_ranges
    
    columns = [
        (1, 'B (功能模块)'),
        (2, 'C (检查点)'),
        (3, 'D (操作步骤)')
    ]
    
    all_merge_ranges = []
    for col_idx, col_name in columns:
        ranges = find_merge_ranges(test_cases, col_idx, START_ROW)
        print(f"   {col_name}: {len(ranges)} 个合并区域")
        all_merge_ranges.extend(ranges)
    
    print(f"   总计: {len(all_merge_ranges)} 个合并区域")
    
    # 3. 批量执行合并（分批，每批 100 个）
    print("\n🔗 执行合并...")
    
    BATCH_SIZE = 100
    total_merged = 0
    failed = 0
    
    for batch_start in range(0, len(all_merge_ranges), BATCH_SIZE):
        batch = all_merge_ranges[batch_start:batch_start + BATCH_SIZE]
        
        requests = []
        for r in batch:
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': r['start_row'],
                        'endRowIndex': r['end_row'],
                        'startColumnIndex': r['col'],
                        'endColumnIndex': r['col'] + 1
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })
        
        try:
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'requests': requests}
            ).execute()
            total_merged += len(batch)
            print(f"   批次 {batch_start // BATCH_SIZE + 1}: 合并 {len(batch)} 个区域 ✅")
        except Exception as e:
            print(f"   批次 {batch_start // BATCH_SIZE + 1}: 失败 - {e}")
            # 逐个尝试
            for r in batch:
                try:
                    sheets_service.spreadsheets().batchUpdate(
                        spreadsheetId=SPREADSHEET_ID,
                        body={'requests': [{
                            'mergeCells': {
                                'range': {
                                    'sheetId': sheet_id,
                                    'startRowIndex': r['start_row'],
                                    'endRowIndex': r['end_row'],
                                    'startColumnIndex': r['col'],
                                    'endColumnIndex': r['col'] + 1
                                },
                                'mergeType': 'MERGE_ALL'
                            }
                        }]}
                    ).execute()
                    total_merged += 1
                except:
                    failed += 1
    
    print(f"\n✅ 合并完成: {total_merged} 成功, {failed} 失败")
    print(f"📎 链接: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")

if __name__ == "__main__":
    main()
