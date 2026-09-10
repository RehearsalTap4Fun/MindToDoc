"""
Google Sheets 写入工具
支持：
1. 在指定文件夹下复制用例模板
2. 在特定分页生成用例
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# 用例模板 ID（默认模板，可通过项目配置 testcase-config/project_config.md 覆盖）
DEFAULT_TEMPLATE_ID = "13bh-0fnsqusJlkRI284rBOG89-pnFH2VyY5NqiD5ScA"

def get_template_id():
    """从项目配置中读取用例模板 ID，若未配置则使用默认值"""
    import json
    config_paths = [
        Path.cwd() / 'testcase-config' / 'config.json',
        Path.cwd().parent / 'testcase-config' / 'config.json',
    ]
    for p in config_paths:
        if p.exists():
            try:
                with open(p) as f:
                    cfg = json.load(f)
                if 'template_sheet_id' in cfg:
                    return cfg['template_sheet_id']
            except Exception:
                pass
    return DEFAULT_TEMPLATE_ID

# 需要完整的读写权限
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class SheetsWriter:
    """Google Sheets 写入器"""
    
    def __init__(self):
        self.sheets_service = None
        self.drive_service = None
        self._init_services()
    
    def _init_services(self):
        """初始化 Google Sheets 和 Drive 服务"""
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        # 优先在 scripts 目录查找，其次在项目根目录
        token_file = script_dir / 'token.json'
        if not token_file.exists():
            token_file = project_root / 'token.json'
        
        if not token_file.exists():
            raise FileNotFoundError(
                "❌ 未找到 token.json\n"
                "请先运行: python3 scripts/auth_setup.py 完成认证\n"
                "注意：需要重新认证以获取写入权限"
            )
        
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        
        # 检查权限是否足够
        if not self._check_write_permission(creds):
            raise PermissionError(
                "❌ 当前令牌没有写入权限\n"
                "请删除 token.json 后重新运行: python3 tools/auth_setup.py"
            )
        
        self.sheets_service = build('sheets', 'v4', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
        print("✅ Google Sheets 写入服务已就绪")
    
    def _check_write_permission(self, creds) -> bool:
        """检查是否有写入权限"""
        if not creds.scopes:
            return False
        return any('spreadsheets' in s and 'readonly' not in s for s in creds.scopes)
    
    # ==================== 文件夹操作 ====================
    
    def copy_template_to_folder(
        self,
        folder_id: str,
        new_name: str,
        template_id: str = DEFAULT_TEMPLATE_ID
    ) -> Optional[str]:
        """
        复制用例模板到指定文件夹
        
        Args:
            folder_id: 目标文件夹 ID
            new_name: 新文件名称
            template_id: 模板文件 ID（默认使用用例模板）
        
        Returns:
            新文件的 ID，失败返回 None
        """
        try:
            # 复制文件
            file_metadata = {
                'name': new_name,
                'parents': [folder_id]
            }
            
            copied_file = self.drive_service.files().copy(
                fileId=template_id,
                body=file_metadata,
                fields='id, name, webViewLink'
            ).execute()
            
            file_id = copied_file.get('id')
            file_name = copied_file.get('name')
            file_link = copied_file.get('webViewLink')
            
            print(f"✅ 已复制模板到文件夹")
            print(f"   文件名: {file_name}")
            print(f"   文件ID: {file_id}")
            print(f"   链接: {file_link}")
            
            return file_id
            
        except HttpError as e:
            print(f"❌ 复制模板失败: {e}")
            return None
    
    def get_folder_id_from_url(self, folder_url: str) -> Optional[str]:
        """
        从文件夹链接提取 ID
        
        Args:
            folder_url: Google Drive 文件夹链接
        
        Returns:
            文件夹 ID
        """
        # 支持多种链接格式
        # https://drive.google.com/drive/folders/xxx
        # https://drive.google.com/drive/u/0/folders/xxx
        import re
        
        patterns = [
            r'folders/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, folder_url)
            if match:
                return match.group(1)
        
        # 如果没有匹配，可能直接是 ID
        if len(folder_url) > 20 and '/' not in folder_url:
            return folder_url
        
        print(f"⚠️ 无法从链接提取文件夹ID: {folder_url}")
        return None
    
    # ==================== 工作表操作 ====================
    
    def get_sheet_list(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        获取文档中的所有工作表
        
        Args:
            spreadsheet_id: 文档 ID
        
        Returns:
            工作表列表 [{'id': xxx, 'title': 'xxx'}, ...]
        """
        try:
            metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheets = []
            for sheet in metadata.get('sheets', []):
                props = sheet.get('properties', {})
                sheets.append({
                    'id': props.get('sheetId'),
                    'title': props.get('title'),
                    'index': props.get('index')
                })
            
            return sheets
            
        except HttpError as e:
            print(f"❌ 获取工作表列表失败: {e}")
            return []
    
    def create_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        index: int = None
    ) -> Optional[int]:
        """
        创建新的工作表
        
        Args:
            spreadsheet_id: 文档 ID
            sheet_name: 工作表名称
            index: 工作表位置（可选）
        
        Returns:
            新工作表的 ID，失败返回 None
        """
        try:
            request = {
                "requests": [{
                    "addSheet": {
                        "properties": {
                            "title": sheet_name
                        }
                    }
                }]
            }
            
            if index is not None:
                request["requests"][0]["addSheet"]["properties"]["index"] = index
            
            result = self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=request
            ).execute()
            
            sheet_id = result['replies'][0]['addSheet']['properties']['sheetId']
            print(f"✅ 已创建工作表: {sheet_name} (ID: {sheet_id})")
            return sheet_id
            
        except HttpError as e:
            if 'already exists' in str(e):
                print(f"⚠️ 工作表 '{sheet_name}' 已存在")
                # 返回已存在的工作表 ID
                sheets = self.get_sheet_list(spreadsheet_id)
                for sheet in sheets:
                    if sheet['title'] == sheet_name:
                        return sheet['id']
            else:
                print(f"❌ 创建工作表失败: {e}")
            return None
    
    def ensure_sheet_exists(
        self,
        spreadsheet_id: str,
        sheet_name: str
    ) -> Optional[int]:
        """
        确保工作表存在，不存在则创建
        
        Args:
            spreadsheet_id: 文档 ID
            sheet_name: 工作表名称
        
        Returns:
            工作表 ID
        """
        sheets = self.get_sheet_list(spreadsheet_id)
        
        for sheet in sheets:
            if sheet['title'] == sheet_name:
                print(f"📋 工作表 '{sheet_name}' 已存在")
                return sheet['id']
        
        return self.create_sheet(spreadsheet_id, sheet_name)
    
    # ==================== 数据写入 ====================
    
    def write_test_cases(
        self,
        spreadsheet_id: str,
        test_cases: List[Dict[str, Any]],
        sheet_name: str = "用例",
        start_row: int = 11,
        include_header: bool = False,
        auto_merge: bool = True
    ) -> bool:
        """
        将测试用例写入指定工作表
        
        Args:
            spreadsheet_id: 文档 ID
            test_cases: 测试用例列表
            sheet_name: 工作表名称
            start_row: 起始行（默认从第11行开始，保护前10行）
            include_header: 是否包含表头（默认不含，模板已有表头）
            auto_merge: 是否自动合并相同内容的单元格
        
        Returns:
            是否成功
        """
        if not test_cases:
            print("⚠️ 没有测试用例可写入")
            return False
        
        # 获取工作表 ID（用于合并单元格）
        sheet_id = self.ensure_sheet_exists(spreadsheet_id, sheet_name)
        
        # 定义列映射（按模板格式）
        # A:编号, B:功能模块, C:检查点, D:操作步骤, E:预期结果, F:备注
        
        # 构建数据矩阵
        values = []
        if include_header:
            headers = ["编号", "功能模块", "检查点", "操作步骤", "预期结果", "备注"]
            values.append(headers)
        
        for tc in test_cases:
            row = [
                tc.get("编号", ""),
                tc.get("模块", tc.get("功能模块", "")),
                tc.get("检查点", ""),
                tc.get("操作步骤", ""),
                tc.get("预期结果", ""),
                tc.get("其他", tc.get("备注", ""))
            ]
            values.append(row)
        
        try:
            # 写入数据
            range_name = f"'{sheet_name}'!A{start_row}"
            body = {"values": values}
            
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            updated_rows = result.get('updatedRows', 0)
            
            print(f"✅ 成功写入 {len(test_cases)} 条测试用例")
            print(f"   工作表: {sheet_name}")
            print(f"   起始行: {start_row}")
            print(f"   更新行数: {updated_rows}")
            
            # 自动合并单元格
            if auto_merge and sheet_id:
                self._auto_merge_cells(spreadsheet_id, sheet_id, test_cases, start_row)
            
            print(f"   📋 链接: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
            
            return True
            
        except HttpError as e:
            print(f"❌ 写入失败: {e}")
            return False
    
    def _auto_merge_cells(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        test_cases: List[Dict[str, Any]],
        start_row: int
    ):
        """
        自动合并相同内容的单元格
        
        合并规则：
        - B列(功能模块): 同模块合并
        - C列(检查点): 同检查点合并
        - D列(操作步骤): 相同步骤合并
        """
        if not test_cases or len(test_cases) < 2:
            return
        
        # 先取消现有合并（B、C、D列，覆盖整个数据区域）
        try:
            end_row = start_row + len(test_cases) + 100  # 多取一些行以确保清理干净
            unmerge_request = {
                "unmergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row - 1,
                        "endRowIndex": end_row,
                        "startColumnIndex": 1,  # B列
                        "endColumnIndex": 4     # 到D列（不含E）
                    }
                }
            }
            
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [unmerge_request]}
            ).execute()
        except HttpError:
            pass  # 忽略取消合并的错误
        
        total_merged = 0
        
        # 收集所有需要合并的请求
        all_merge_requests = []
        columns_to_merge = [
            ("模块", 1),      # B列
            ("检查点", 2),    # C列
            ("操作步骤", 3),  # D列
        ]
        
        for field, col_index in columns_to_merge:
            requests = self._find_merge_ranges(test_cases, field, col_index, start_row, sheet_id)
            all_merge_requests.extend(requests)
        
        # 逐个执行合并请求（跳过失败的）
        for req in all_merge_requests:
            try:
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": [req]}
                ).execute()
                total_merged += 1
            except HttpError:
                pass  # 跳过失败的合并请求
        
        if total_merged > 0:
            print(f"   ✅ 已合并 {total_merged} 个单元格区域")
    
    def _find_merge_ranges(
        self,
        test_cases: List[Dict[str, Any]],
        field: str,
        col_index: int,
        start_row: int,
        sheet_id: int
    ) -> List[Dict]:
        """
        查找需要合并的单元格范围
        """
        merge_requests = []
        
        # 兼容不同字段名
        field_aliases = {
            "模块": ["模块", "功能模块"],
            "检查点": ["检查点"],
            "操作步骤": ["操作步骤"]
        }
        
        aliases = field_aliases.get(field, [field])
        
        i = 0
        while i < len(test_cases):
            # 获取当前值
            current_value = None
            for alias in aliases:
                current_value = test_cases[i].get(alias)
                if current_value:
                    break
            
            if not current_value:
                i += 1
                continue
            
            # 查找连续空值的范围（空字符串表示需要合并到上一个非空值）
            j = i + 1
            while j < len(test_cases):
                next_value = None
                for alias in aliases:
                    next_value = test_cases[j].get(alias)
                    if next_value:
                        break
                
                # 如果下一行是空字符串或None，继续合并
                # 如果下一行有新值，停止合并
                if next_value == "" or next_value is None:
                    j += 1
                else:
                    break
            
            # 如果有多行需要合并，添加合并请求
            if j - i > 1:
                merge_requests.append({
                    "mergeCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row - 1 + i,  # 0-indexed
                            "endRowIndex": start_row - 1 + j,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        },
                        "mergeType": "MERGE_ALL"
                    }
                })
            
            i = j
        
        return merge_requests
    
    def append_test_cases(
        self,
        spreadsheet_id: str,
        test_cases: List[Dict[str, Any]],
        sheet_name: str = "用例"
    ) -> bool:
        """
        追加测试用例到工作表末尾
        
        Args:
            spreadsheet_id: 文档 ID
            test_cases: 测试用例列表
            sheet_name: 工作表名称
        
        Returns:
            是否成功
        """
        if not test_cases:
            print("⚠️ 没有测试用例可追加")
            return False
        
        # 构建数据矩阵（不含表头）
        values = []
        for tc in test_cases:
            row = [
                tc.get("编号", ""),
                tc.get("模块", ""),
                tc.get("检查点", ""),
                tc.get("操作步骤", ""),
                tc.get("预期结果", ""),
                tc.get("关联配置表", ""),
                tc.get("其他", "")
            ]
            values.append(row)
        
        try:
            range_name = f"'{sheet_name}'!A:G"
            body = {"values": values}
            
            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            
            updates = result.get('updates', {})
            updated_rows = updates.get('updatedRows', 0)
            
            print(f"✅ 成功追加 {updated_rows} 条测试用例")
            return True
            
        except HttpError as e:
            print(f"❌ 追加失败: {e}")
            return False
    
    def clear_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        keep_header: bool = True
    ) -> bool:
        """
        清空工作表内容
        
        Args:
            spreadsheet_id: 文档 ID
            sheet_name: 工作表名称
            keep_header: 是否保留表头
        
        Returns:
            是否成功
        """
        try:
            start_row = 2 if keep_header else 1
            range_name = f"'{sheet_name}'!A{start_row}:Z1000"
            
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            print(f"✅ 已清空工作表: {sheet_name}")
            return True
            
        except HttpError as e:
            print(f"❌ 清空失败: {e}")
            return False


# ==================== 便捷函数 ====================

def find_template_in_folder(folder_id: str, template_keyword: str = "用例模板") -> Optional[str]:
    """
    在文件夹中查找模板文件
    
    Args:
        folder_id: 文件夹 ID
        template_keyword: 模板文件名关键词
    
    Returns:
        模板文件 ID
    """
    writer = SheetsWriter()
    
    try:
        results = writer.drive_service.files().list(
            q=f"'{folder_id}' in parents and name contains '{template_keyword}'",
            fields='files(id, name)',
            orderBy='name'
        ).execute()
        
        files = results.get('files', [])
        if files:
            template = files[0]
            print(f"📋 找到模板: {template['name']}")
            return template['id']
        else:
            print(f"⚠️ 未找到包含 '{template_keyword}' 的模板文件")
            return None
            
    except Exception as e:
        print(f"❌ 查找模板失败: {e}")
        return None


def create_testcase_file(
    folder_url: str,
    file_name: str,
    template_id: str = None,
    use_folder_template: bool = True
) -> Optional[str]:
    """
    在指定文件夹创建测试用例文件（复制模板）
    
    Args:
        folder_url: 文件夹链接或 ID
        file_name: 新文件名称
        template_id: 模板 ID（可选，不提供则自动查找文件夹内的模板）
        use_folder_template: 是否使用文件夹内的模板
    
    Returns:
        新文件 ID
    """
    writer = SheetsWriter()
    
    # 提取文件夹 ID
    folder_id = writer.get_folder_id_from_url(folder_url)
    if not folder_id:
        return None
    
    # 如果没有指定模板，尝试在文件夹中查找
    if not template_id and use_folder_template:
        template_id = find_template_in_folder(folder_id)
    
    # 如果还是没有，使用默认模板
    if not template_id:
        template_id = DEFAULT_TEMPLATE_ID
        print(f"📋 使用默认模板")
    
    return writer.copy_template_to_folder(folder_id, file_name, template_id)


def write_cases_to_sheet(
    spreadsheet_id: str,
    test_cases: List[Dict[str, Any]],
    sheet_name: str = "用例"
) -> bool:
    """
    将测试用例写入指定文档的工作表
    
    Args:
        spreadsheet_id: 文档 ID
        test_cases: 测试用例列表
        sheet_name: 工作表名称
    
    Returns:
        是否成功
    """
    writer = SheetsWriter()
    return writer.write_test_cases(spreadsheet_id, test_cases, sheet_name)


def create_and_write(
    folder_url: str,
    file_name: str,
    test_cases: List[Dict[str, Any]],
    sheet_name: str = "用例",
    template_id: str = None
) -> Optional[str]:
    """
    一站式操作：在文件夹中复制模板并写入用例
    
    Args:
        folder_url: 文件夹链接或 ID
        file_name: 新文件名称
        test_cases: 测试用例列表
        sheet_name: 工作表名称
        template_id: 模板 ID（可选，不提供则自动查找文件夹内的模板）
    
    Returns:
        新文件 ID
    """
    writer = SheetsWriter()
    
    # 1. 提取文件夹 ID
    folder_id = writer.get_folder_id_from_url(folder_url)
    if not folder_id:
        return None
    
    # 2. 如果没有指定模板，尝试在文件夹中查找
    if not template_id:
        template_id = find_template_in_folder(folder_id)
    
    # 如果还是没有，使用默认模板
    if not template_id:
        template_id = DEFAULT_TEMPLATE_ID
        print(f"📋 使用默认模板")
    
    # 3. 复制模板
    file_id = writer.copy_template_to_folder(folder_id, file_name, template_id)
    if not file_id:
        return None
    
    # 4. 写入用例
    writer.write_test_cases(file_id, test_cases, sheet_name)
    
    return file_id


# ==================== 测试 ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 Google Sheets 写入工具测试")
    print("="*60)
    
    # 示例测试用例
    sample_cases = [
        {
            "编号": "HSDS_001",
            "模块": "红色斗士系统",
            "检查点": "入口显示",
            "操作步骤": "1. 打开游戏主界面\n2. 查看红色斗士入口",
            "预期结果": "1. 入口图标正确显示\n2. 红点逻辑正确",
            "关联配置表": "hero_config",
            "其他": "P0"
        },
        {
            "编号": "HSDS_002",
            "模块": "红色斗士系统",
            "检查点": "斗士列表",
            "操作步骤": "1. 点击红色斗士入口\n2. 查看斗士列表",
            "预期结果": "1. 列表正确加载\n2. 斗士信息显示正确",
            "关联配置表": "hero_config",
            "其他": "P0"
        }
    ]
    
    try:
        writer = SheetsWriter()
        print("\n✅ 写入工具初始化成功")
        print("\n📝 使用方法:")
        print("   1. 复制模板到文件夹:")
        print("      create_testcase_file(folder_url, '测试用例_功能名')")
        print("   2. 写入用例到工作表:")
        print("      write_cases_to_sheet(spreadsheet_id, test_cases, '用例')")
        print("   3. 一站式操作:")
        print("      create_and_write(folder_url, '测试用例_功能名', test_cases)")
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        print("\n📝 解决方法:")
        print("   1. 删除项目根目录的 token.json")
        print("   2. 修改 tools/auth_setup.py 的 SCOPES 为读写权限")
        print("   3. 重新运行: python3 tools/auth_setup.py")
