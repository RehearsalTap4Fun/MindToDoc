#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用用例写入脚本 - 完整版

功能：
1. 查找最新周期目录
2. 复制模板文件
3. 填充空单元格（B/C/D列）
4. 扩展行数（如需要）
5. 复制格式（边框、底色、下拉选项）
6. 写入用例数据
7. 合并单元格
8. 写入变更记录模板内容（M15:M24, S15:S24）

使用方法：
    python write_cases_to_sheet.py <json_file> <功能名称>
    
示例：
    python write_cases_to_sheet.py ../K1-testcase-config/output/valentine_team_testcases.json 情人节组队活动_相伴生长
"""

# 跟踪表配置（用于自动提取 PRD 链接 + 团队人员信息 + 更新进度）
TRACKER_SPREADSHEET_ID = '1PuOpAhfByj6-B_JUb_2tcQr4DfQJqAIq9iauubJMTC0'


def get_team_info_from_tracker(sheets_service, period_num, row_idx):
    """从跟踪表对应版本 sheet 的指定行读取 F/G/H 列（策划/客户端/服务器）
    
    Args:
        sheets_service: Google Sheets 服务实例
        period_num: 周期编号（如 577）
        row_idx: 跟踪表中的行号（1-indexed）
    
    Returns:
        (planner, client, server) 三元组，缺失则为 '无'
    """
    sheet_name = f'{period_num}版本'
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=TRACKER_SPREADSHEET_ID,
            range=f'{sheet_name}!F{row_idx}:H{row_idx}'
        ).execute()
        row = result.get('values', [[]])[0] if result.get('values') else []
        def cell(i):
            return row[i].strip() if i < len(row) and row[i].strip() else '无'
        return cell(0), cell(1), cell(2)
    except Exception as e:
        print(f"   ⚠️ 跟踪表团队信息读取失败: {e}")
        return '无', '无', '无'


def find_prd_link_from_tracker(sheets_service, period_num, feature_name):
    """从跟踪表的对应版本 sheet 中，按 C 列文本模糊匹配 feature_name，提取 C 列超链接
    
    Args:
        sheets_service: Google Sheets 服务实例
        period_num: 周期编号（如 577）
        feature_name: 功能名称（用于模糊匹配 C 列）
    
    Returns:
        (matched_row, c_text, prd_url) 或 (None, None, None) 找不到时
    """
    sheet_name = f'{period_num}版本'
    try:
        result = sheets_service.spreadsheets().get(
            spreadsheetId=TRACKER_SPREADSHEET_ID,
            ranges=[f'{sheet_name}!C1:C100'],
            includeGridData=True,
            fields='sheets(data(rowData(values(userEnteredValue,hyperlink))))'
        ).execute()
    except Exception as e:
        print(f"   ⚠️ 跟踪表读取失败（sheet={sheet_name}）: {e}")
        return None, None, None
    
    sheets_data = result.get('sheets', [])
    if not sheets_data:
        return None, None, None
    rows = sheets_data[0].get('data', [{}])[0].get('rowData', [])
    
    # 通用词作为停止词，避免误匹配（"优化"、"活动"等）
    STOPWORDS = {
        '优化', '活动', '系统', '功能', '用例', '测试', '需求', '版本',
        '新增', '调整', '升级', '修改', '更新', '修复', '增加',
        '一期', '二期', '三期', '1期', '2期', '3期', '期',
        '新版', '新', '旧',
    }
    
    # 别名映射（左边的关键词在 feature_name 出现时，等同于右边的）
    # 用于跨表名匹配
    ALIAS = {
        '龙吟沙漠': ['巨龙之战', '龙吟', '巨龙'],
        '周年回顾': ['周年庆', '周年报', '5周年', '年报'],
        '克里斯': ['哈罗德', '克里斯'],
        '疯狂哈罗德': ['哈罗德', '克里斯'],
        '闪电抢购': ['秒杀抢购', '秒杀', '抢购'],
        '周年欢宴': ['做饭', '周年庆做饭', '宴会', '欢宴'],
        '至尊特权': ['VIP专属皮肤', '专属皮肤', '至尊'],
        'VIP等级提升': ['VIP专属皮肤', 'VIP'],
    }
    
    def tokens(s):
        """拆分并过滤停止词、单字；同时剥离停止词后缀
        例：'疯狂哈罗德优化' → '疯狂哈罗德'（去掉后缀 '优化'）
        """
        out = []
        for token in re.split(r'[_（）()\s\-\.和、/]+', s):
            token = token.strip()
            if not token:
                continue
            # 反复剥离末尾的停止词（如 '疯狂哈罗德优化' → '疯狂哈罗德'）
            changed = True
            while changed:
                changed = False
                for sw in STOPWORDS:
                    if len(token) > len(sw) and token.endswith(sw):
                        token = token[:-len(sw)]
                        changed = True
                        break
            if len(token) >= 2 and token not in STOPWORDS:
                out.append(token)
        return out
    
    def expand_with_alias(toks):
        """加入别名词"""
        expanded = list(toks)
        for t in toks:
            if t in ALIAS:
                expanded.extend(ALIAS[t])
        return expanded
    
    feat_tokens = expand_with_alias(tokens(feature_name))
    
    best_match = None  # (row, score, c_text, hl)
    for i, r in enumerate(rows, 1):
        values = r.get('values', [])
        if not values:
            continue
        v = values[0]
        c_text = v.get('userEnteredValue', {}).get('stringValue', '') or ''
        hl = v.get('hyperlink')
        if not c_text or not hl:
            continue
        # 评分：c_text 包含的 feat_token 越长越多分越高
        score = 0
        c_tokens = expand_with_alias(tokens(c_text))
        for ft in feat_tokens:
            if ft in c_text:
                score += len(ft)  # 长 token 权重更高
        for ct in c_tokens:
            if ct in feature_name:
                score += len(ct) // 2
        if score == 0:
            continue
        if best_match is None or score > best_match[1]:
            best_match = (i, score, c_text, hl)
    
    # 设置最低分阈值，避免误匹配（至少匹配到 3 个字符以上的 token）
    if best_match and best_match[1] >= 3:
        row, score, c_text, hl = best_match
        return row, c_text, hl
    return None, None, None


# 变更记录 sheet 模板配置
CHANGE_LOG_CONFIG = {
    # M15 标题
    'title': 'AI用例问题',
    'title_cell': 'M15',
    # M15 格式：12号字体、加粗、浅紫色背景
    'title_format': {
        'backgroundColor': {'red': 0.8352941, 'green': 0.6509804, 'blue': 0.7411765},
        'textFormat': {'fontSize': 12, 'bold': True}
    },
    # M16:S24 合并区域
    'content_range': {
        'startRowIndex': 15,  # M16
        'endRowIndex': 24,    # 到24行
        'startColumnIndex': 12,  # M
        'endColumnIndex': 19     # S
    },
    # 内容文本
    'content_text': '衍生检查点遗漏：\n1、\n2、\n…\n\n案子不明确导致测试点遗漏或无效检查：\n1、\n2、\n…\n\n测试点冗余：\n1、\n2、\n…\n\n没有相关需求生成的无效检查：\n1、\n2、\n…',
    # 富文本格式：小标题橙色，内容黑色
    'content_runs': [
        {'startIndex': 0, 'format': {'foregroundColor': {'red': 0.9, 'green': 0.5, 'blue': 0.1}}},   # 衍生检查点遗漏：
        {'startIndex': 8, 'format': {'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}}},         # \n1、\n2、\n…\n\n
        {'startIndex': 18, 'format': {'foregroundColor': {'red': 0.9, 'green': 0.5, 'blue': 0.1}}},  # 案子不明确导致测试点遗漏或无效检查：
        {'startIndex': 36, 'format': {'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}}},        # \n1、\n2、\n…\n\n
        {'startIndex': 46, 'format': {'foregroundColor': {'red': 0.9, 'green': 0.5, 'blue': 0.1}}},  # 测试点冗余：
        {'startIndex': 52, 'format': {'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}}},        # \n1、\n2、\n…\n\n
        {'startIndex': 62, 'format': {'foregroundColor': {'red': 0.9, 'green': 0.5, 'blue': 0.1}}},  # 没有相关需求生成的无效检查：
        {'startIndex': 76, 'format': {'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}}},        # \n1、\n2、\n…
    ]
}

import json
import sys
import time
import re
from pathlib import Path


def get_google_services():
    """获取 Google API 服务"""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    
    token_file = Path(__file__).parent / 'token.json'
    if not token_file.exists():
        print(f"❌ 未找到 token.json: {token_file}")
        sys.exit(1)
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, 'w') as f:
            f.write(creds.to_json())
    
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return sheets_service, drive_service


def fill_empty_cells(test_cases):
    """填充空单元格 - B/C/D列空值自动继承上方内容"""
    filled = []
    current_b, current_c, current_d = "", "", ""
    
    for row in test_cases:
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


def find_merge_ranges(data, col_index, start_row, sheet_id):
    """计算需要合并的单元格区域"""
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
            if next_value == '' or next_value is None or next_value == current_value:
                j += 1
            else:
                break
        if j - i > 1:
            merge_ranges.append({
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
    return merge_ranges


def _ranges_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def find_case_area_unmerge_requests(sheet_metadata, sheet_id, start_row, end_row,
                                    start_col=1, end_col=4):
    """Find existing merges in the case table columns before re-merging groups."""
    requests = []
    row_start = start_row - 1
    row_end = end_row
    for sheet in sheet_metadata.get('sheets', []):
        if sheet['properties']['sheetId'] != sheet_id:
            continue
        for merge_range in sheet.get('merges', []):
            if not _ranges_overlap(merge_range['startRowIndex'], merge_range['endRowIndex'], row_start, row_end):
                continue
            if not _ranges_overlap(merge_range['startColumnIndex'], merge_range['endColumnIndex'], start_col, end_col):
                continue
            requests.append({'unmergeCells': {'range': {
                'sheetId': sheet_id,
                'startRowIndex': merge_range['startRowIndex'],
                'endRowIndex': merge_range['endRowIndex'],
                'startColumnIndex': merge_range['startColumnIndex'],
                'endColumnIndex': merge_range['endColumnIndex'],
            }}})
    return requests


def extract_period_num(folder_name):
    """从周期文件夹名提取编号，如 '565（3.9~3.13）共5D' -> 565"""
    match = re.match(r'^(\d+)', folder_name)
    return int(match.group(1)) if match else 0


def find_latest_folder(drive_service, root_folder_id):
    """查找最新的周期文件夹"""
    def list_folder(folder_id):
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType)",
            orderBy="name desc"
        ).execute()
        return results.get('files', [])
    
    # 查找年份文件夹
    items = list_folder(root_folder_id)
    year_folders = [f for f in items if f['mimeType'] == 'application/vnd.google-apps.folder']
    
    # 选择最新年份（优先 2026年 或 2026）
    target_year = None
    for f in year_folders:
        if f['name'] in ['2026', '2026年']:
            target_year = f
            break
    if not target_year:
        for f in year_folders:
            if f['name'].replace('年', '').isdigit():
                target_year = f
                break
    
    if not target_year:
        print("❌ 未找到年份文件夹")
        return None, None, None
    
    print(f"   年份: {target_year['name']}")
    
    # 查找周期文件夹
    items = list_folder(target_year['id'])
    period_folders = [f for f in items if f['mimeType'] == 'application/vnd.google-apps.folder']
    period_folders.sort(key=lambda x: extract_period_num(x['name']), reverse=True)
    
    if not period_folders:
        print("❌ 未找到周期文件夹")
        return None, None, None
    
    target_period = period_folders[0]
    period_num = extract_period_num(target_period['name'])
    print(f"   周期: {target_period['name']}")
    
    # 查找模板文件（优先周期文件夹内，找不到则回退到根目录）
    items = list_folder(target_period['id'])
    template_file = None
    for f in items:
        if '模板' in f['name'] and f['mimeType'] != 'application/vnd.google-apps.folder':
            template_file = f
            break

    # 回退：周期文件夹内没有模板时，使用根目录的「用例模板」
    if not template_file:
        for f in list_folder(root_folder_id):
            if ('用例模板' in f['name'] or '功能名称_用例模板' in f['name']) \
                    and f['mimeType'] == 'application/vnd.google-apps.spreadsheet':
                template_file = f
                break

    if not template_file:
        print("❌ 未找到用例模板（周期文件夹和根目录均未找到）")
        return None, None, None
    
    print(f"   模板: {template_file['name']}")
    
    return target_period['id'], period_num, template_file['id']


def write_test_cases(json_file, feature_name, feature_type='功能优化', prd_url=None):
    """完整的用例写入流程
    
    Args:
        json_file: JSON 用例文件路径
        feature_name: 功能名称（用于命名文件和填写变更记录的功能名称字段）
        feature_type: 功能类型（变更记录 G9 下拉值），可选值：
            通用用例 / 框架复用 / 新功能 / 新活动 / 大型&复杂系统 /
            纯客户端 / 纯服务器 / 通识类 / 功能优化 / 检查点
        prd_url: PRD/需求链接，会写入用例 sheet 的 B6:E8 合并单元格，显示文本为
            feature_name，超链接为 prd_url（蓝色下划线）。None 则不填写。
    """
    
    # 读取配置
    config_file = Path(__file__).parent.parent / "K1-testcase-config/project_config.md"
    ROOT_FOLDER_ID = "1wtQhEaTrW2B6E9uLm_lnyT8XNiZ2dKbJ"  # 默认值
    
    # 尝试从配置文件读取
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'用例根目录 ID.*?`([^`]+)`', content)
            if match:
                ROOT_FOLDER_ID = match.group(1)
    
    print("=" * 60)
    print("📝 用例写入脚本")
    print("=" * 60)
    
    # 1. 连接 Google API
    print("\n🔌 连接 Google API...")
    sheets_service, drive_service = get_google_services()
    print("   ✅ 连接成功")
    
    # 2. 读取用例数据
    print(f"\n📖 读取用例数据: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)
    
    # 支持两种格式
    if isinstance(test_cases, dict) and 'test_cases' in test_cases:
        test_cases = test_cases['test_cases']
    
    print(f"   共 {len(test_cases)} 条用例")
    
    # 保存原始数据用于计算合并区域
    original_test_cases = [list(row) for row in test_cases]
    
    # 填充空单元格
    test_cases = fill_empty_cells(test_cases)
    print("   ✅ 已填充空单元格")
    
    # 3. 查找最新周期目录
    print("\n📁 查找目录结构...")
    folder_id, period_num, template_id = find_latest_folder(drive_service, ROOT_FOLDER_ID)
    
    if not folder_id:
        sys.exit(1)
    
    # 4. 复制模板
    print("\n📋 复制模板...")
    new_name = f"{period_num}_AI_{feature_name}"
    
    copied_file = drive_service.files().copy(
        fileId=template_id,
        body={'name': new_name, 'parents': [folder_id]},
        fields='id, name, webViewLink'
    ).execute()
    
    spreadsheet_id = copied_file['id']
    print(f"   文件名: {new_name}")
    print(f"   ID: {spreadsheet_id}")
    
    # 5. 获取工作表信息
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    current_rows = 0
    for sheet in sheet_metadata.get('sheets', []):
        if sheet['properties']['title'] == '用例':
            sheet_id = sheet['properties']['sheetId']
            current_rows = sheet['properties']['gridProperties']['rowCount']
            break
    
    if sheet_id is None:
        print("❌ 未找到 '用例' 工作表")
        sys.exit(1)
    
    START_ROW = 11
    END_ROW = START_ROW + len(test_cases) - 1
    required_rows = END_ROW + 20
    
    # 6. 扩展行数（如需要）
    if current_rows < required_rows:
        print(f"\n📐 扩展行数: {current_rows} → {required_rows}")
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [{'appendDimension': {
                'sheetId': sheet_id,
                'dimension': 'ROWS',
                'length': required_rows - current_rows + 50
            }}]}
        ).execute()
        print("   ✅ 行数已扩展")
        time.sleep(1)
    
    # 7. 复制格式（边框、底色）
    print("\n🎨 复制格式...")
    SOURCE_ROW = 11
    BATCH_SIZE = 20
    
    for batch_start in range(START_ROW + 1, END_ROW + 2, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, END_ROW + 2)
        
        requests = []
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
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
        except:
            pass
        time.sleep(0.5)
    
    print("   ✅ 格式已复制")
    
    # 8. 复制数据验证（G/H/I列下拉选项）
    print("\n📋 复制数据验证...")
    for col_idx in [6, 7, 8]:
        for batch_start in range(START_ROW + 1, END_ROW + 2, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, END_ROW + 2)
            
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
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute()
            except:
                pass
            time.sleep(0.3)
    
    print("   ✅ 数据验证已复制")
    
    # 9. 写入用例数据
    print("\n✍️ 写入用例数据...")
    WRITE_BATCH = 50
    
    for i in range(0, len(test_cases), WRITE_BATCH):
        batch = test_cases[i:i + WRITE_BATCH]
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
        time.sleep(0.5)
    
    print("   ✅ 数据写入完成")
    
    # 10. 合并单元格
    print("\n🔗 合并单元格...")
    
    # 计算合并区域
    merge_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    unmerge_requests = find_case_area_unmerge_requests(merge_metadata, sheet_id, START_ROW, END_ROW)
    if unmerge_requests:
        for i in range(0, len(unmerge_requests), 50):
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': unmerge_requests[i:i + 50]}
            ).execute()
            time.sleep(0.3)
        print(f"   cleared stale merges: {len(unmerge_requests)}")

    all_merge_requests = []
    for col_idx in [1, 2, 3]:
        all_merge_requests.extend(find_merge_ranges(original_test_cases, col_idx, START_ROW, sheet_id))
    
    print(f"   共 {len(all_merge_requests)} 个合并区域")
    
    # 分批执行合并
    MERGE_BATCH = 20
    success = 0
    
    for i in range(0, len(all_merge_requests), MERGE_BATCH):
        batch = all_merge_requests[i:i + MERGE_BATCH]
        try:
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': batch}
            ).execute()
            success += len(batch)
        except Exception as e:
            print(f"   merge batch failed: {e}")
        time.sleep(1)
    
    print(f"   ✅ 合并 {success}/{len(all_merge_requests)} 个区域")
    
    # 10.5 清除模板残留行 + B 列整列加边框
    # 模板内容到第 264 行，预留缓冲清到第 280 行
    TEMPLATE_LAST = 280
    clear_start = END_ROW + 1
    if clear_start <= TEMPLATE_LAST:
        print(f"\n🧹 清除模板残留行 (行 {clear_start} ~ {TEMPLATE_LAST}) ...")
        # 收集残留区域内的合并先取消
        cur_meta = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        residue_merges = []
        for s in cur_meta.get('sheets', []):
            if s['properties']['sheetId'] != sheet_id:
                continue
            for m in s.get('merges', []):
                if m['startRowIndex'] >= clear_start - 1 and m['endRowIndex'] <= TEMPLATE_LAST:
                    residue_merges.append(m)
                elif m['startRowIndex'] < TEMPLATE_LAST and m['endRowIndex'] > clear_start - 1:
                    residue_merges.append(m)
        clear_requests = []
        for m in residue_merges:
            clear_requests.append({'unmergeCells': {'range': {
                'sheetId': sheet_id,
                'startRowIndex': m['startRowIndex'], 'endRowIndex': m['endRowIndex'],
                'startColumnIndex': m['startColumnIndex'], 'endColumnIndex': m['endColumnIndex']
            }}})
        clear_requests.append({'updateCells': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': clear_start - 1, 'endRowIndex': TEMPLATE_LAST,
                'startColumnIndex': 0, 'endColumnIndex': 10
            },
            'fields': 'userEnteredValue,userEnteredFormat,textFormatRuns,dataValidation,note,hyperlink'
        }})
        try:
            for i in range(0, len(clear_requests), 50):
                sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': clear_requests[i:i+50]}
                ).execute()
                time.sleep(0.3)
            print(f"   ✅ 已清除残留（取消 {len(residue_merges)} 个合并、清空内容/格式）")
        except Exception as e:
            print(f"   ⚠️ 清除残留失败: {e}")
    
    # B 列整列统一加边框（修复合并末尾边框断开问题）
    print("\n🖼️ 统一 B 列边框...")
    try:
        BORDER = {'style': 'SOLID', 'width': 1, 'color': {'red': 0, 'green': 0, 'blue': 0}}
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [{
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': START_ROW - 1,
                        'endRowIndex': END_ROW,
                        'startColumnIndex': 1,
                        'endColumnIndex': 2,
                    },
                    'right': BORDER,
                    'bottom': BORDER,
                    'innerHorizontal': BORDER,
                }
            }]}
        ).execute()
        print(f"   ✅ B{START_ROW}:B{END_ROW} 边框已统一")
    except Exception as e:
        print(f"   ⚠️ B 列边框统一失败: {e}")
    
    # 11. 写入变更记录模板内容
    print("\n📝 写入变更记录模板...")
    try:
        # 获取变更记录sheet的ID
        change_log_sheet_id = None
        for sheet in sheet_metadata.get('sheets', []):
            if sheet['properties']['title'] == '变更记录':
                change_log_sheet_id = sheet['properties']['sheetId']
                break
        
        if change_log_sheet_id is not None:
            # 写入M15标题
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"变更记录!{CHANGE_LOG_CONFIG['title_cell']}",
                valueInputOption='USER_ENTERED',
                body={'values': [[CHANGE_LOG_CONFIG['title']]]}
            ).execute()
            
            # 设置M15格式 + 合并M16:S24
            content_range = CHANGE_LOG_CONFIG['content_range']
            requests = [
                # M15格式：背景色、字体
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': change_log_sheet_id,
                            'startRowIndex': 14,
                            'endRowIndex': 15,
                            'startColumnIndex': 12,
                            'endColumnIndex': 13
                        },
                        'cell': {
                            'userEnteredFormat': CHANGE_LOG_CONFIG['title_format']
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                    }
                },
                # 合并M16:S24
                {
                    'mergeCells': {
                        'range': {
                            'sheetId': change_log_sheet_id,
                            **content_range
                        },
                        'mergeType': 'MERGE_ALL'
                    }
                },
                # M16垂直对齐顶部
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': change_log_sheet_id,
                            'startRowIndex': content_range['startRowIndex'],
                            'endRowIndex': content_range['startRowIndex'] + 1,
                            'startColumnIndex': content_range['startColumnIndex'],
                            'endColumnIndex': content_range['startColumnIndex'] + 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'verticalAlignment': 'TOP',
                                'wrapStrategy': 'WRAP'
                            }
                        },
                        'fields': 'userEnteredFormat(verticalAlignment,wrapStrategy)'
                    }
                }
            ]
            
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
            # 写入M16富文本内容
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [{
                    'updateCells': {
                        'rows': [{
                            'values': [{
                                'userEnteredValue': {'stringValue': CHANGE_LOG_CONFIG['content_text']},
                                'textFormatRuns': CHANGE_LOG_CONFIG['content_runs']
                            }]
                        }],
                        'fields': 'userEnteredValue,textFormatRuns',
                        'range': {
                            'sheetId': change_log_sheet_id,
                            'startRowIndex': content_range['startRowIndex'],
                            'endRowIndex': content_range['startRowIndex'] + 1,
                            'startColumnIndex': content_range['startColumnIndex'],
                            'endColumnIndex': content_range['startColumnIndex'] + 1
                        }
                    }
                }]}
            ).execute()
            
            print("   ✅ 变更记录模板已写入")
        else:
            print("   ⚠️ 未找到变更记录工作表")
    except Exception as e:
        print(f"   ⚠️ 变更记录写入失败: {e}")
    
    # 12. 填写变更记录字段（时间/操作员/操作说明/功能名称/设计人员/定稿条数/功能类型）
    print("\n🗓️ 填写变更记录字段...")
    try:
        from datetime import datetime
        today = datetime.now().strftime('%Y.%m.%d')
        case_count = len(test_cases)
        fill_data = [
            {'range': '变更记录!A3', 'values': [[today]]},
            {'range': '变更记录!B3', 'values': [['AI']]},
            {'range': '变更记录!C3', 'values': [['新建']]},
            {'range': '变更记录!E3', 'values': [[f'共 {case_count} 条']]},
            {'range': '变更记录!C8', 'values': [[feature_name]]},
            {'range': '变更记录!C9', 'values': [['AI']]},
            {'range': '变更记录!E9', 'values': [[case_count]]},
            {'range': '变更记录!G9', 'values': [[feature_type]]},
        ]
        sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'valueInputOption': 'USER_ENTERED', 'data': fill_data}
        ).execute()
        print(f"   ✅ 时间={today} | 操作员=AI | 共{case_count}条 | 功能类型={feature_type}")
    except Exception as e:
        print(f"   ⚠️ 变更记录字段填写失败: {e}")
    
    # 12.5 从跟踪表匹配功能行（一次匹配，复用给 PRD 链接 + 团队信息）
    matched_row, c_text = None, None
    print(f"\n🔎 在跟踪表 {period_num}版本 sheet 中匹配功能行...")
    matched_row, c_text, auto_url = find_prd_link_from_tracker(
        sheets_service, period_num, feature_name
    )
    if matched_row:
        print(f"   ✅ 匹配到行{matched_row}: \"{c_text}\"")
    else:
        print(f"   ⚠️ 跟踪表中未找到匹配项")
    
    # 13. 写入 A1 团队信息：策划/客户端/服务器（来自跟踪表 F/G/H 列）
    if matched_row:
        print(f"\n👥 写入 A1 团队信息...")
        try:
            planner, client, server = get_team_info_from_tracker(
                sheets_service, period_num, matched_row
            )
            a1_text = f'策划：{planner}，客户端：{client}，服务器：{server}'
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='用例!A1',
                valueInputOption='USER_ENTERED',
                body={'values': [[a1_text]]}
            ).execute()
            print(f"   ✅ A1 = {a1_text}")
        except Exception as e:
            print(f"   ⚠️ A1 团队信息写入失败: {e}")
    
    # 14. 写入 PRD 链接到 B6（如果未显式传入则用自动匹配的）
    if not prd_url:
        prd_url = auto_url
    
    if prd_url:
        print(f"\n🔗 写入 PRD 链接到 B6: {prd_url}")
        try:
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [{
                    'updateCells': {
                        'rows': [{
                            'values': [{
                                'userEnteredValue': {'stringValue': feature_name},
                                'textFormatRuns': [{
                                    'startIndex': 0,
                                    'format': {
                                        'foregroundColor': {'red': 0.067, 'green': 0.333, 'blue': 0.8},
                                        'underline': True,
                                        'link': {'uri': prd_url}
                                    }
                                }]
                            }]
                        }],
                        'fields': 'userEnteredValue,textFormatRuns',
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 5,  # B6 → 行索引 5
                            'endRowIndex': 6,
                            'startColumnIndex': 1,  # B
                            'endColumnIndex': 2
                        }
                    }
                }]}
            ).execute()
            print(f"   ✅ B6 已填写 \"{feature_name}\" + 超链接")
        except Exception as e:
            print(f"   ⚠️ PRD 链接写入失败: {e}")
    else:
        print(f"\n⚠️ 未提供 prd_url 参数，B6 未填写需求链接")
    
    # 完成
    print("\n" + "=" * 60)
    print(f"🎉 完成！共写入 {len(test_cases)} 条测试用例")
    print(f"📎 https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print("=" * 60)
    
    return spreadsheet_id


def main():
    if len(sys.argv) < 3:
        print("用法: python write_cases_to_sheet.py <json_file> <功能名称> [功能类型] [PRD链接]")
        print()
        print("功能类型可选值（默认 '功能优化'）：")
        print("  通用用例 / 框架复用 / 新功能 / 新活动 / 大型&复杂系统 /")
        print("  纯客户端 / 纯服务器 / 通识类 / 功能优化 / 检查点")
        print()
        print("示例:")
        print("  python write_cases_to_sheet.py ../output/test_cases.json 情人节组队活动 新活动 https://jira.tap4fun.com/browse/NK-6158")
        sys.exit(1)
    
    json_file = sys.argv[1]
    feature_name = sys.argv[2]
    feature_type = sys.argv[3] if len(sys.argv) >= 4 else '功能优化'
    prd_url = sys.argv[4] if len(sys.argv) >= 5 else None
    
    if not Path(json_file).exists():
        print(f"❌ 文件不存在: {json_file}")
        sys.exit(1)
    
    write_test_cases(json_file, feature_name, feature_type, prd_url)


if __name__ == "__main__":
    main()
