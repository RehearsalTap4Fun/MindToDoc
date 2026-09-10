"""
Google Sheets OAuth 认证设置
基于 google-workspace-mcp-with-script 项目
"""
import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 如果修改了权限范围，删除 token.json 文件重新认证
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',  # 读写权限
    'https://www.googleapis.com/auth/drive'          # 读写权限（复制文件需要）
]

class GoogleSheetsAuth:
    """Google Sheets OAuth 认证管理器"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        # 优先在 scripts 目录查找，其次在项目根目录
        self.credentials_file = self.script_dir / 'credentials.json'
        if not self.credentials_file.exists():
            self.credentials_file = self.project_root / 'credentials.json'
        self.token_file = self.script_dir / 'token.json'
        self.creds = None
    
    def authenticate(self):
        """执行 OAuth 认证流程"""
        print("\n" + "="*60)
        print("🔐 Google Sheets OAuth 认证")
        print("="*60)
        
        # 检查是否已有有效令牌
        if self.token_file.exists():
            print("📦 检测到现有令牌...")
            self.creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
        
        # 如果没有有效令牌，或令牌已过期
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("🔄 刷新过期令牌...")
                self.creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    print("\n❌ 错误: 未找到 credentials.json")
                    print("\n📝 请按以下步骤获取:")
                    print("1. 访问 Google Cloud Console: https://console.cloud.google.com/")
                    print("2. 创建新项目或选择现有项目")
                    print("3. 启用 Google Sheets API 和 Google Drive API")
                    print("4. 配置 OAuth 同意屏幕:")
                    print("   - 用户类型: 外部")
                    print("   - 添加测试用户: 你的 Gmail 地址")
                    print("5. 创建凭据:")
                    print("   - 凭据 > 创建凭据 > OAuth 客户端 ID")
                    print("   - 应用类型: 桌面应用")
                    print("   - 下载 JSON 文件")
                    print(f"6. 将文件重命名为 credentials.json 并放到:")
                    print(f"   {self.credentials_file}")
                    return False
                
                print("🌐 启动 OAuth 认证流程...")
                print("📢 浏览器将打开，请登录你的 Google 账号并授权访问")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), 
                    SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # 保存令牌供下次使用
            print("💾 保存认证令牌...")
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())
        
        print("✅ 认证成功!")
        return True
    
    def get_sheets_service(self):
        """获取 Google Sheets 服务实例"""
        if not self.creds:
            if not self.authenticate():
                return None
        
        try:
            service = build('sheets', 'v4', credentials=self.creds)
            return service
        except Exception as e:
            print(f"❌ 创建服务失败: {e}")
            return None
    
    def test_connection(self):
        """测试连接"""
        print("\n" + "="*60)
        print("🧪 测试 Google Sheets 连接")
        print("="*60)
        
        service = self.get_sheets_service()
        if not service:
            return False
        
        # 从配置文件读取测试用的 Sheet ID
        config_path = Path(__file__).parent / "config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            test_spreadsheet_id = config.get("google_sheet_id", "")
        else:
            print("❌ 未找到 config.json，请先配置 google_sheet_id")
            return False
        
        try:
            print(f"\n📋 测试读取 Sheet ID: {test_spreadsheet_id}")
            
            # 获取表格信息
            sheet_metadata = service.spreadsheets().get(
                spreadsheetId=test_spreadsheet_id
            ).execute()
            
            print(f"✅ 表格名称: {sheet_metadata.get('properties', {}).get('title')}")
            
            # 列出所有 Sheet
            sheets = sheet_metadata.get('sheets', [])
            print(f"✅ 包含 {len(sheets)} 个工作表:")
            for sheet in sheets[:5]:  # 只显示前5个
                sheet_title = sheet.get('properties', {}).get('title')
                print(f"   - {sheet_title}")
            
            # 尝试读取第一个 Sheet 的数据
            if sheets:
                first_sheet = sheets[0].get('properties', {}).get('title')
                range_name = f"{first_sheet}!A1:Z10"
                
                result = service.spreadsheets().values().get(
                    spreadsheetId=test_spreadsheet_id,
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                print(f"\n✅ 成功读取数据:")
                print(f"   - 范围: {range_name}")
                print(f"   - 行数: {len(values)}")
                if values:
                    print(f"   - 表头: {values[0]}")
            
            print("\n✅ 连接测试成功!")
            return True
            
        except Exception as e:
            print(f"\n❌ 连接测试失败: {e}")
            return False


def main():
    """主函数"""
    print("\n" + "🚀"*30)
    print("Google Sheets OAuth 认证设置")
    print("🚀"*30)
    
    auth = GoogleSheetsAuth()
    
    # 执行认证
    if auth.authenticate():
        # 测试连接
        auth.test_connection()
        
        print("\n" + "="*60)
        print("✅ 设置完成!")
        print("="*60)
        print("\n📝 下一步:")
        print("   1. credentials.json 和 token.json 已就绪")
        print("   2. 运行 python3 tools/excel_tool.py 测试数据读取")
        print("   3. 开始使用测试用例生成功能")
        print()
    else:
        print("\n❌ 认证失败，请按提示完成设置")


if __name__ == '__main__':
    main()
