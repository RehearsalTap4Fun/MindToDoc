#!/usr/bin/env python3
"""
将测试用例JSON批量写入Google Sheets
一次性创建Sheet并写入所有数据，完整填充每个单元格（不使用合并）
"""

import json
import sys
from pathlib import Path

def main():
    # 获取参数
    if len(sys.argv) < 3:
        print("用法: python write_testcases_complete.py <json_file> <folder_id>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    folder_id = sys.argv[2]
    
    # 读取JSON数据
    with open(json_file, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)
    
    print(f"✅ 读取 {len(test_cases)} 条测试用例")
    
    # 初始化OAuth
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("❌ 缺少 Google API 库")
        sys.exit(1)
    
    # 查找token.json
    possible_paths = [
        Path(__file__).parent / 'token.json',
        Path(__file__).parent.parent / 'token.json',
    ]
    
    token_file = None
    for path in possible_paths:
        if path.exists():
            token_file = path
            break
    
    if not token_file:
        print("❌ 未找到 token.json")
        sys.exit(1)
    
    # 创建凭证
    creds = Credentials.from_authorized_user_file(str(token_file))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, 'w') as f:
            f.write(creds.to_json())
    
    # 创建服务
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # 1. 创建新的电子表格
    spreadsheet_name = "0.85.0_AI_集卡图鉴系统_测试用例_完整版"
    
    spreadsheet = sheets_service.spreadsheets().create(body={
        'properties': {'title': spreadsheet_name},
        'sheets': [{
            'properties': {
                'title': '测试用例',
                'gridProperties': {
                    'rowCount': len(test_cases) + 10,
                    'columnCount': 6
                }
            }
        }]
    }).execute()
    
    sheet_id = spreadsheet['spreadsheetId']
    print(f"✅ 创建电子表格: {spreadsheet_name}")
    print(f"   ID: {sheet_id}")
    
    # 2. 移动到目标文件夹
    drive_service.files().update(
        fileId=sheet_id,
        addParents=folder_id,
        removeParents='root',
        fields='id, parents'
    ).execute()
    print(f"✅ 移动到文件夹: {folder_id}")
    
    # 3. 准备数据（完整填充每个单元格）
    # 表头
    header = ["用例编号", "功能模块", "检查点", "操作步骤", "预期结果", "备注"]
    
    # 转换数据，填充空的功能模块和检查点
    rows = [header]
    current_module = ""
    current_checkpoint = ""
    
    for tc in test_cases:
        # tc格式: [编号, 功能模块, 检查点, 操作步骤, 预期结果, 备注]
        case_id = tc[0] if len(tc) > 0 else ""
        module = tc[1] if len(tc) > 1 and tc[1] else current_module
        checkpoint = tc[2] if len(tc) > 2 and tc[2] else current_checkpoint
        step = tc[3] if len(tc) > 3 else ""
        expected = tc[4] if len(tc) > 4 else ""
        remark = tc[5] if len(tc) > 5 else ""
        
        # 更新当前值
        if tc[1]:
            current_module = tc[1]
        if tc[2]:
            current_checkpoint = tc[2]
        
        rows.append([case_id, module, checkpoint, step, expected, remark])
    
    print(f"✅ 准备 {len(rows)} 行数据（含表头）")
    
    # 4. 批量写入数据（分批，每批500行）
    batch_size = 500
    total_rows = len(rows)
    
    for i in range(0, total_rows, batch_size):
        batch = rows[i:i + batch_size]
        start_row = i + 1  # 1-indexed
        end_row = start_row + len(batch) - 1
        
        range_name = f"测试用例!A{start_row}:F{end_row}"
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption='RAW',
            body={'values': batch}
        ).execute()
        
        print(f"   写入行 {start_row}-{end_row}")
    
    # 5. 格式化表头（加粗、背景色）
    sheet_props = spreadsheet['sheets'][0]['properties']['sheetId']
    
    requests = [
        # 表头背景色
        {
            'repeatCell': {
                'range': {
                    'sheetId': sheet_props,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 6
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.7},
                        'textFormat': {
                            'bold': True,
                            'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}
                        },
                        'horizontalAlignment': 'CENTER'
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
            }
        },
        # 冻结表头
        {
            'updateSheetProperties': {
                'properties': {
                    'sheetId': sheet_props,
                    'gridProperties': {'frozenRowCount': 1}
                },
                'fields': 'gridProperties.frozenRowCount'
            }
        },
        # 设置列宽
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_props,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 1
                },
                'properties': {'pixelSize': 90},
                'fields': 'pixelSize'
            }
        },
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_props,
                    'dimension': 'COLUMNS',
                    'startIndex': 1,
                    'endIndex': 2
                },
                'properties': {'pixelSize': 120},
                'fields': 'pixelSize'
            }
        },
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_props,
                    'dimension': 'COLUMNS',
                    'startIndex': 2,
                    'endIndex': 3
                },
                'properties': {'pixelSize': 160},
                'fields': 'pixelSize'
            }
        },
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_props,
                    'dimension': 'COLUMNS',
                    'startIndex': 3,
                    'endIndex': 4
                },
                'properties': {'pixelSize': 280},
                'fields': 'pixelSize'
            }
        },
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_props,
                    'dimension': 'COLUMNS',
                    'startIndex': 4,
                    'endIndex': 5
                },
                'properties': {'pixelSize': 280},
                'fields': 'pixelSize'
            }
        },
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_props,
                    'dimension': 'COLUMNS',
                    'startIndex': 5,
                    'endIndex': 6
                },
                'properties': {'pixelSize': 120},
                'fields': 'pixelSize'
            }
        }
    ]
    
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={'requests': requests}
    ).execute()
    
    print("✅ 格式化完成")
    
    # 输出结果
    print("\n" + "=" * 60)
    print(f"🎉 完成！共写入 {len(test_cases)} 条测试用例")
    print(f"📎 链接: https://docs.google.com/spreadsheets/d/{sheet_id}")
    print("=" * 60)
    
    return sheet_id

if __name__ == "__main__":
    main()
