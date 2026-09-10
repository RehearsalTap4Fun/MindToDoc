#!/usr/bin/env python3
"""
修复用例表格格式问题
- 复制模板行的格式（边框、底色、下拉选项）到所有数据行
"""

import time
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def main():
    SPREADSHEET_ID = "1LsrAkUm1drGT7CKKfwtxsjO8srLUgWAraLxzJudoRnY"
    
    token_file = Path(__file__).parent / 'token.json'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    sheets_service = build('sheets', 'v4', credentials=creds)
    print("✅ Google API 连接成功")
    
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
    
    # 配置
    SOURCE_ROW = 11         # 格式源行（第11行有完整格式）
    START_ROW = 12          # 从第12行开始复制格式
    END_ROW = 270           # 用例结束行（多留一些余量）
    
    print(f"\n📐 复制格式和数据验证: 从第 {SOURCE_ROW} 行复制到第 {START_ROW}-{END_ROW} 行")
    
    # 方法1：逐行复制格式
    print("\n🎨 复制边框和底色...")
    
    # 每次复制一行的格式到多行
    BATCH_SIZE = 20
    
    for batch_start in range(START_ROW, END_ROW + 1, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, END_ROW + 1)
        
        print(f"   处理行 {batch_start}-{batch_end-1}...")
        
        requests = []
        
        # 对每一行单独复制格式
        for row in range(batch_start, batch_end):
            requests.append({
                'copyPaste': {
                    'source': {
                        'sheetId': sheet_id,
                        'startRowIndex': SOURCE_ROW - 1,
                        'endRowIndex': SOURCE_ROW,
                        'startColumnIndex': 0,
                        'endColumnIndex': 10
                    },
                    'destination': {
                        'sheetId': sheet_id,
                        'startRowIndex': row - 1,
                        'endRowIndex': row,
                        'startColumnIndex': 0,
                        'endColumnIndex': 10
                    },
                    'pasteType': 'PASTE_FORMAT'
                }
            })
        
        try:
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'requests': requests}
            ).execute()
            print(f"      ✅ 格式已复制")
        except Exception as e:
            print(f"      ⚠️ 失败: {str(e)[:60]}")
        
        time.sleep(1)
    
    # 方法2：复制数据验证（G/H/I 列的下拉选项）
    print("\n📋 复制数据验证（下拉选项）...")
    
    for col_idx in [6, 7, 8]:  # G=6, H=7, I=8 (0-indexed)
        col_name = chr(65 + col_idx)
        print(f"   {col_name} 列...")
        
        # 逐行复制数据验证
        for batch_start in range(START_ROW, END_ROW + 1, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, END_ROW + 1)
            
            requests = []
            for row in range(batch_start, batch_end):
                requests.append({
                    'copyPaste': {
                        'source': {
                            'sheetId': sheet_id,
                            'startRowIndex': SOURCE_ROW - 1,
                            'endRowIndex': SOURCE_ROW,
                            'startColumnIndex': col_idx,
                            'endColumnIndex': col_idx + 1
                        },
                        'destination': {
                            'sheetId': sheet_id,
                            'startRowIndex': row - 1,
                            'endRowIndex': row,
                            'startColumnIndex': col_idx,
                            'endColumnIndex': col_idx + 1
                        },
                        'pasteType': 'PASTE_DATA_VALIDATION'
                    }
                })
            
            try:
                sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body={'requests': requests}
                ).execute()
            except Exception as e:
                print(f"      ⚠️ 行 {batch_start}-{batch_end-1} 失败")
            
            time.sleep(0.5)
        
        print(f"      ✅ {col_name} 列完成")
    
    print("\n" + "=" * 60)
    print("🎉 格式修复完成！")
    print(f"📎 https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print("=" * 60)

if __name__ == "__main__":
    main()
