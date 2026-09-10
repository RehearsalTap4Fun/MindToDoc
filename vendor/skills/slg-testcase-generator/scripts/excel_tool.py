"""
Excel/Google Sheets 数据处理工具
供 Claude 调用来读取和解析配置表数据
支持 OAuth 认证
"""
import sys
import json
import csv
from typing import List, Dict, Any, Optional
from io import StringIO
from pathlib import Path

# Windows 编码修复
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    import codecs
    if not isinstance(sys.stdout, codecs.StreamWriter):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')


class SheetDataReader:
    """Google Sheets 数据读取器 (使用 OAuth)"""
    
    def __init__(self, sheet_id: str, use_oauth: bool = True):
        """
        初始化读取器
        
        Args:
            sheet_id: Google Sheets 的文档ID
            use_oauth: 是否使用 OAuth 认证（推荐）
        """
        self.sheet_id = sheet_id
        self.use_oauth = use_oauth
        self.cache = {}
        self.service = None
        
        if use_oauth:
            self._init_oauth_service()
        
        print(f"✅ 初始化 SheetDataReader，文档ID: {sheet_id}")
        print(f"   认证方式: {'OAuth 2.0' if use_oauth else 'CSV Export'}")
    
    def _init_oauth_service(self):
        """初始化 OAuth 服务"""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            # 尝试多个可能的 token.json 位置
            possible_paths = [
                Path(__file__).parent / 'token.json',  # scripts/token.json
                Path(__file__).parent.parent / 'token.json',  # skill/token.json
                Path(__file__).parent.parent.parent.parent / 'token.json',  # qa/token.json
            ]

            token_file = None
            for path in possible_paths:
                if path.exists():
                    token_file = path
                    break

            if not token_file:
                print("\n⚠️  未找到 token.json，请先运行:")
                print("   python scripts/auth_setup.py")
                self.use_oauth = False
                return

            # 从 token.json 读取凭证（使用 token 中保存的 scopes）
            creds = Credentials.from_authorized_user_file(str(token_file))

            # 检查 token 是否过期，如果过期则刷新
            if creds.expired and creds.refresh_token:
                print("🔄 Token 已过期，正在刷新...")
                creds.refresh(Request())
                # 保存刷新后的 token
                with open(token_file, 'w') as f:
                    f.write(creds.to_json())
                print("✅ Token 已刷新并保存")

            self.service = build('sheets', 'v4', credentials=creds)
            print("✅ OAuth 认证服务已就绪")
            
        except ImportError:
            print("\n⚠️  缺少 Google API 库，请安装:")
            print("   pip3 install google-auth-oauthlib google-api-python-client")
            self.use_oauth = False
        except Exception as e:
            print(f"\n⚠️  OAuth 初始化失败: {e}")
            self.use_oauth = False
    
    def read_sheet(self, gid: str = None, sheet_name: str = "", range_name: str = None) -> List[Dict[str, Any]]:
        """
        读取指定sheet的数据
        
        Args:
            gid: Sheet的GID (仅用于CSV模式)
            sheet_name: Sheet名称
            range_name: 数据范围，如 "Sheet1!A1:Z1000"
            
        Returns:
            List[Dict]: 数据列表，每行为一个字典
        """
        cache_key = f"{gid}_{sheet_name}_{range_name}"
        
        # 检查缓存
        if cache_key in self.cache:
            print(f"📦 从缓存读取: {sheet_name or gid}")
            return self.cache[cache_key]
        
        print(f"\n{'='*60}")
        print(f"📥 开始读取: {sheet_name or range_name or f'GID={gid}'}")
        print(f"{'='*60}")
        
        # 使用 OAuth 方式读取
        if self.use_oauth and self.service:
            try:
                data = self._read_with_oauth(sheet_name, range_name)
                self.cache[cache_key] = data
                return data
            except Exception as e:
                print(f"❌ OAuth 读取失败: {e}")
                print("🔄 回退到 CSV 模式...")
                self.use_oauth = False
        
        # 使用 CSV 导出方式读取（需要公开访问）
        return self._read_with_csv(gid, sheet_name)
    
    def _read_with_oauth(self, sheet_name: str, range_name: str = None) -> List[Dict[str, Any]]:
        """使用 OAuth 方式读取"""
        # 如果没有指定范围，先获取所有 sheet
        if not range_name:
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            sheets = sheet_metadata.get('sheets', [])
            
            # 如果指定了 sheet_name，使用它；否则使用第一个
            if sheet_name:
                target_sheet = sheet_name
            elif sheets:
                target_sheet = sheets[0].get('properties', {}).get('title')
            else:
                raise Exception("未找到可用的工作表")
            
            range_name = f"{target_sheet}"
        
        print(f"📋 读取范围: {range_name}")
        
        # 读取数据
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            print("⚠️  未读取到数据")
            return []
        
        # 转换为字典列表
        headers = values[0]
        data = []
        
        for row in values[1:]:
            # 补齐行数据（处理不完整的行）
            while len(row) < len(headers):
                row.append('')
            
            row_dict = dict(zip(headers, row))
            data.append(row_dict)
        
        print(f"✅ 成功读取 {len(data)} 行数据")
        print(f"📊 表头: {headers}")
        if data:
            print(f"📝 第一行示例: {data[0]}")
        
        return data
    
    def _read_with_csv(self, gid: str, sheet_name: str) -> List[Dict[str, Any]]:
        """使用 CSV 导出方式读取（需要公开访问）"""
        url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv&gid={gid}"
        print(f"🔗 URL: {url}")
        print("⚠️  注意: CSV 模式需要 Sheet 设置为公开访问")
        
        try:
            import requests
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 解析CSV数据
            csv_data = StringIO(response.text)
            reader = csv.DictReader(csv_data)
            data = list(reader)
            
            print(f"✅ 成功读取 {len(data)} 行数据")
            if data:
                print(f"📊 表头: {list(data[0].keys())}")
                print(f"📝 第一行示例: {data[0]}")
            
            return data
            
        except Exception as e:
            print(f"❌ CSV 读取失败: {e}")
            return []
    
    def read_raw_values(self, sheet_name: str = "", range_name: str = None) -> List[List[Any]]:
        """
        读取原始值（不做表头转换）

        用于处理合并单元格、非标准表头的情况。
        返回二维数组，每个元素是单元格内容。

        Args:
            sheet_name: Sheet名称
            range_name: 数据范围，如 "Sheet1!A1:Z1000"

        Returns:
            List[List]: 原始数据的二维数组
        """
        if not self.use_oauth or not self.service:
            print("❌ read_raw_values 需要 OAuth 认证")
            return []

        try:
            # 如果没有指定范围，使用 sheet_name
            if not range_name:
                if sheet_name:
                    range_name = sheet_name
                else:
                    # 获取第一个 sheet 的名称
                    sheet_metadata = self.service.spreadsheets().get(
                        spreadsheetId=self.sheet_id
                    ).execute()
                    sheets = sheet_metadata.get('sheets', [])
                    if sheets:
                        range_name = sheets[0].get('properties', {}).get('title')
                    else:
                        print("❌ 未找到可用的工作表")
                        return []

            print(f"📋 读取原始数据: {range_name}")

            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])

            print(f"✅ 成功读取 {len(values)} 行原始数据")
            if values:
                print(f"📝 第一行预览: {values[0][:5]}...")

            return values

        except Exception as e:
            print(f"❌ 读取原始数据失败: {e}")
            return []

    def find_header_row(self, values: List[List[Any]], keywords: List[str] = None) -> int:
        """
        智能查找真正的表头行

        用于处理合并单元格导致的表头偏移问题。
        查找包含关键词的行作为真正的表头。

        Args:
            values: read_raw_values 返回的原始数据
            keywords: 期望的表头关键词列表，默认为常见表头词

        Returns:
            表头行的索引，未找到返回 0
        """
        if keywords is None:
            keywords = ['用例编号', '模块', '功能', '检查点', '步骤', '预期结果', '优先级']

        for idx, row in enumerate(values[:20]):  # 只检查前20行
            row_text = ' '.join(str(cell) for cell in row if cell)
            matches = sum(1 for kw in keywords if kw in row_text)
            if matches >= 2:  # 至少匹配2个关键词
                print(f"🔍 找到表头行: 第 {idx + 1} 行 (匹配 {matches} 个关键词)")
                return idx

        print("⚠️ 未找到表头行，使用第一行作为表头")
        return 0

    def values_to_dicts(self, values: List[List[Any]], header_row: int = 0) -> List[Dict[str, Any]]:
        """
        将原始值转换为字典列表

        Args:
            values: read_raw_values 返回的原始数据
            header_row: 表头行索引

        Returns:
            List[Dict]: 转换后的字典列表
        """
        if not values or header_row >= len(values):
            return []

        headers = [str(h).strip() if h else f'列{i}' for i, h in enumerate(values[header_row])]

        data = []
        for row in values[header_row + 1:]:
            # 补齐行数据
            while len(row) < len(headers):
                row.append('')

            row_dict = dict(zip(headers, row))
            data.append(row_dict)

        print(f"✅ 转换 {len(data)} 行数据，表头: {headers[:5]}...")
        return data

    def list_sheets(self) -> List[Dict[str, Any]]:
        """列出所有工作表"""
        if not self.use_oauth or not self.service:
            print("❌ 需要 OAuth 认证才能列出工作表")
            return []
        
        try:
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            sheets = sheet_metadata.get('sheets', [])
            
            result = []
            for sheet in sheets:
                props = sheet.get('properties', {})
                result.append({
                    'title': props.get('title'),
                    'sheetId': props.get('sheetId'),
                    'index': props.get('index'),
                    'sheetType': props.get('sheetType')
                })
            
            return result
            
        except Exception as e:
            print(f"❌ 列出工作表失败: {e}")
            return []
    
    def get_headers(self, data: List[Dict[str, Any]]) -> List[str]:
        """获取表头"""
        if data:
            return list(data[0].keys())
        return []
    
    def filter_rows(self, data: List[Dict[str, Any]], 
                   conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据条件筛选行"""
        result = []
        for row in data:
            match = True
            for key, value in conditions.items():
                if key not in row or row[key] != value:
                    match = False
                    break
            if match:
                result.append(row)
        return result
    
    def group_by(self, data: List[Dict[str, Any]], 
                 key: str) -> Dict[str, List[Dict[str, Any]]]:
        """按指定字段分组"""
        groups = {}
        for row in data:
            group_key = row.get(key, "未分类")
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(row)
        return groups


class ConfigAnalyzer:
    """配置表分析器"""
    
    @staticmethod
    def validate_number_range(value: Any, min_val: float, max_val: float) -> bool:
        """验证数值范围"""
        pass
    
    @staticmethod
    def validate_probability_sum(config_list: List[Dict[str, Any]], 
                                prob_field: str = "概率") -> Dict[str, Any]:
        """验证概率总和"""
        pass
    
    @staticmethod
    def analyze_config_structure(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析配置表结构"""
        pass


class TestPointExtractor:
    """测试要点提取器"""
    
    @staticmethod
    def extract_from_prd(prd_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从PRD中提取测试要点"""
        pass
    
    @staticmethod
    def extract_from_config(config_data: List[Dict[str, Any]], 
                          config_type: str) -> Dict[str, Any]:
        """从配置表中提取验证点"""
        pass


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 Google Sheets 数据读取测试")
    print("="*60)
    
    # 从配置文件读取 Sheet ID
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("❌ 未找到 config.json，请先配置 google_sheet_id")
        sys.exit(1)
    with open(config_path, 'r') as f:
        _config = json.load(f)
    SHEET_ID = _config.get("google_sheet_id", "")
    
    # 创建读取器（优先使用 OAuth）
    reader = SheetDataReader(SHEET_ID, use_oauth=True)
    
    # 列出所有工作表
    print("\n" + "🔍 步骤1: 列出所有工作表")
    sheets = reader.list_sheets()
    if sheets:
        print(f"✅ 找到 {len(sheets)} 个工作表:")
        for i, sheet in enumerate(sheets, 1):
            print(f"   {i}. {sheet['title']} (ID: {sheet['sheetId']})")
    
    # 测试1: 读取第一个工作表
    if sheets:
        first_sheet = sheets[0]['title']
        print(f"\n" + "🔍 步骤2: 读取工作表 '{first_sheet}'")
        data = reader.read_sheet(sheet_name=first_sheet)
        
        if data:
            print(f"\n✅ 读取成功!")
            print(f"   - 总行数: {len(data)}")
            print(f"   - 表头: {reader.get_headers(data)}")
            print(f"\n📋 前3行数据预览:")
            for i, row in enumerate(data[:3], 1):
                print(f"\n   行{i}:")
                for key, value in list(row.items())[:5]:  # 只显示前5列
                    print(f"      {key}: {value}")
            
            # 测试数据操作
            print(f"\n" + "🔍 步骤3: 测试数据操作")
            headers = reader.get_headers(data)
            if headers:
                first_field = headers[0]
                groups = reader.group_by(data, first_field)
                print(f"✅ 按 '{first_field}' 分组:")
                for group_name, items in list(groups.items())[:5]:
                    print(f"   - {group_name}: {len(items)} 项")
        else:
            print("\n❌ 读取失败!")
    
    print("\n" + "="*60)
    print("✅ 测试完成!")
    print("="*60)
    print("\n💡 提示:")
    if reader.use_oauth:
        print("   ✅ 使用 OAuth 认证，无需公开 Sheet")
    else:
        print("   ⚠️  使用 CSV 模式，需要 Sheet 公开访问")
        print("   💡 建议运行: python3 tools/auth_setup.py")
    print()
