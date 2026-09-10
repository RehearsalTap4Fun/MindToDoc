#!/usr/bin/env python3
"""
情人节组队活动用例写入脚本
1. 查找最新版本目录
2. 复制模板
3. 写入用例数据
"""

import json
import sys
from pathlib import Path

def main():
    # 配置
    ROOT_FOLDER_ID = "1wtQhEaTrW2B6E9uLm_lnyT8XNiZ2dKbJ"  # 用例根目录
    JSON_FILE = Path(__file__).parent.parent / "K1-testcase-config/output/valentine_team_testcases.json"
    
    # 初始化 Google API
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("❌ 缺少 Google API 库，请运行: pip install google-api-python-client google-auth-oauthlib")
        sys.exit(1)
    
    # 查找 token.json
    token_file = Path(__file__).parent / 'token.json'
    if not token_file.exists():
        print(f"❌ 未找到 token.json: {token_file}")
        sys.exit(1)
    
    # 创建凭证
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, 'w') as f:
            f.write(creds.to_json())
    
    # 创建服务
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    print("✅ Google API 连接成功")
    
    # 1. 查找目录结构: 根目录 -> 年份 -> 季度 -> 版本
    print("\n📁 查找目录结构...")
    
    def list_folder(folder_id):
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType)",
            orderBy="name desc"
        ).execute()
        return results.get('files', [])
    
    # 查找最新年份
    years = list_folder(ROOT_FOLDER_ID)
    year_folders = [f for f in years if f['mimeType'] == 'application/vnd.google-apps.folder']
    print(f"   年份文件夹: {[f['name'] for f in year_folders[:5]]}")
    
    # 选择 2026年 或 2026 或最新年份
    target_year = None
    for f in year_folders:
        if f['name'] in ['2026', '2026年']:
            target_year = f
            break
    if not target_year:
        # 按数字排序找最新年份
        for f in year_folders:
            if f['name'].replace('年', '').isdigit():
                target_year = f
                break
    if not target_year and year_folders:
        target_year = year_folders[0]
    
    if not target_year:
        print("❌ 未找到年份文件夹")
        sys.exit(1)
    print(f"   选择年份: {target_year['name']}")
    
    # 查找周期/季度文件夹
    quarters = list_folder(target_year['id'])
    quarter_folders = [f for f in quarters if f['mimeType'] == 'application/vnd.google-apps.folder']
    print(f"   周期文件夹: {[f['name'] for f in quarter_folders]}")
    
    # 选择最新周期 (按数字排序，如 565 > 564)
    def extract_period_num(name):
        """提取周期编号，如 '565（3.9~3.13）共5D' -> 565"""
        import re
        match = re.match(r'^(\d+)', name)
        return int(match.group(1)) if match else 0
    
    quarter_folders.sort(key=lambda x: extract_period_num(x['name']), reverse=True)
    target_quarter = quarter_folders[0] if quarter_folders else None
    if not target_quarter:
        print("❌ 未找到周期文件夹")
        sys.exit(1)
    print(f"   选择周期: {target_quarter['name']}")
    
    # 检查周期文件夹内容 - 可能直接是文件，也可能有版本子文件夹
    items_in_quarter = list_folder(target_quarter['id'])
    version_folders = [f for f in items_in_quarter if f['mimeType'] == 'application/vnd.google-apps.folder']
    
    if version_folders:
        # 有版本子文件夹，选择最新版本
        print(f"   版本文件夹: {[f['name'] for f in version_folders]}")
        target_version = version_folders[0]
        print(f"   选择版本: {target_version['name']}")
        target_folder_id = target_version['id']
        files_in_version = list_folder(target_version['id'])
    else:
        # 没有版本子文件夹，直接使用周期文件夹
        print(f"   无版本子文件夹，直接使用周期文件夹")
        target_folder_id = target_quarter['id']
        files_in_version = items_in_quarter
    template_file = None
    for f in files_in_version:
        if '模板' in f['name'] and '用例' in f['name']:
            template_file = f
            break
    
    if not template_file:
        print("❌ 未找到用例模板")
        print(f"   可用文件: {[f['name'] for f in files_in_version[:10]]}")
        sys.exit(1)
    print(f"   模板文件: {template_file['name']}")
    
    # 2. 复制模板
    print("\n📋 复制模板...")
    # 从周期文件夹名称提取编号作为文件名前缀
    period_num = extract_period_num(target_quarter['name'])
    new_name = f"{period_num}_AI_情人节组队活动_相伴生长"
    
    copied_file = drive_service.files().copy(
        fileId=template_file['id'],
        body={
            'name': new_name,
            'parents': [target_folder_id]
        },
        fields='id, name, webViewLink'
    ).execute()
    
    spreadsheet_id = copied_file['id']
    print(f"✅ 创建文件: {new_name}")
    print(f"   ID: {spreadsheet_id}")
    
    # 3. 读取用例数据
    print("\n📖 读取用例数据...")
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)
    print(f"   共 {len(test_cases)} 条用例")
    
    # 保存原始数据用于计算合并区域
    original_test_cases = [list(row) for row in test_cases]
    
    # 填充空单元格，确保每个单元格都有内容
    def fill_empty_cells(data):
        filled = []
        current_b, current_c, current_d = "", "", ""
        for row in data:
            new_row = list(row)
            if len(new_row) > 1:
                if new_row[1]: current_b = new_row[1]
                else: new_row[1] = current_b
            if len(new_row) > 2:
                if new_row[2]: current_c = new_row[2]
                else: new_row[2] = current_c
            if len(new_row) > 3:
                if new_row[3]: current_d = new_row[3]
                else: new_row[3] = current_d
            filled.append(new_row)
        return filled
    
    test_cases = fill_empty_cells(test_cases)
    print(f"   ✅ 已填充空单元格")
    
    # 4. 检查并扩展工作表行数
    print("\n📐 检查工作表行数...")
    START_ROW = 11
    required_rows = START_ROW + len(test_cases) + 10  # 预留一些余量
    
    # 获取当前工作表信息
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    current_rows = 0
    for sheet in sheet_metadata.get('sheets', []):
        if sheet['properties']['title'] == '用例':
            sheet_id = sheet['properties']['sheetId']
            current_rows = sheet['properties']['gridProperties']['rowCount']
            break
    
    print(f"   当前行数: {current_rows}, 需要行数: {required_rows}")
    
    # 如果行数不足，添加更多行
    if current_rows < required_rows and sheet_id is not None:
        rows_to_add = required_rows - current_rows + 50  # 多加一些
        print(f"   添加 {rows_to_add} 行...")
        
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
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
        print(f"   ✅ 行数已扩展到 {current_rows + rows_to_add}")
    
    # 5. 写入用例数据
    print("\n✍️ 写入用例数据...")
    
    BATCH_SIZE = 50
    
    for i in range(0, len(test_cases), BATCH_SIZE):
        batch = test_cases[i:i + BATCH_SIZE]
        start_row = START_ROW + i
        end_row = start_row + len(batch) - 1
        range_name = f"用例!A{start_row}:F{end_row}"
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body={'values': batch}
        ).execute()
        
        print(f"   写入行 {start_row}-{end_row}")
    
    # 6. 合并单元格 (B/C/D 列)
    print("\n🔗 合并单元格...")
    
    # 获取 sheet ID
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    for sheet in sheet_metadata.get('sheets', []):
        if sheet['properties']['title'] == '用例':
            sheet_id = sheet['properties']['sheetId']
            break
    
    if sheet_id is not None:
        # 计算合并区域
        def find_merge_ranges(data, col_index, start_row):
            """找出需要合并的单元格范围"""
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
        
        all_merge_requests = []
        for col_idx in [1, 2, 3]:  # B, C, D 列
            # 使用原始数据计算合并区域（原始数据中空字符串表示需要合并）
            all_merge_requests.extend(find_merge_ranges(original_test_cases, col_idx, START_ROW))
        
        if all_merge_requests:
            # 分批执行合并
            for req in all_merge_requests:
                try:
                    sheets_service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={'requests': [req]}
                    ).execute()
                except Exception:
                    pass  # 跳过失败的合并
            print(f"   合并 {len(all_merge_requests)} 个区域")
    
    # 输出结果
    print("\n" + "=" * 60)
    print(f"🎉 完成！共写入 {len(test_cases)} 条测试用例")
    print(f"📎 链接: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print("=" * 60)
    
    return spreadsheet_id

if __name__ == "__main__":
    main()
