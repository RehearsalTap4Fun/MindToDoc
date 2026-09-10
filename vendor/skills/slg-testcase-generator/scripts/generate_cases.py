#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例生成主入口
完整工作流：读取 → 分析 → 提取 → 生成 → 写入
"""
import sys
import io
import json
import argparse
from pathlib import Path
from typing import Optional

# 设置标准输出为 UTF-8（解决 Windows 编码问题）
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')

# 添加脚本目录到 path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from excel_tool import SheetDataReader
from config_analyzer import ConfigAnalyzer
from testpoint_extractor import TestPointExtractor, TestPoint
from case_generator import CaseGenerator


def print_banner():
    """打印横幅"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                  SLG 测试用例生成器                           ║
║                                                              ║
║  📋 PRD分析 → 🔍 配置挖掘 → 📝 用例生成 → 📤 输出            ║
╚══════════════════════════════════════════════════════════════╝
    """)


def generate_test_cases(
    sheet_id: str,
    prd_sheet: str,
    config_sheet: Optional[str] = None,
    func_type: str = "D",
    case_prefix: str = "TC",
    output_format: str = "markdown",
    output_path: Optional[str] = None,
    output_folder: Optional[str] = None,
    file_name: Optional[str] = None,
    use_gemini: bool = False
) -> dict:
    """
    生成测试用例完整流程

    Args:
        sheet_id: Google Sheets 文档ID
        prd_sheet: PRD工作表名称
        config_sheet: 配置表工作表名称（可选）
        func_type: 功能类型 A/B/C/D
        case_prefix: 用例编号前缀
        output_format: 输出格式 (markdown/json/sheets)
        output_path: 输出文件路径
        output_folder: Google Drive 文件夹URL（用于sheets输出）
        file_name: 输出文件名（用于sheets输出）
        use_gemini: 是否使用 Gemini 智能解析非结构化文档

    Returns:
        生成结果字典
    """
    result = {
        'success': False,
        'message': '',
        'case_count': 0,
        'output': None
    }

    # Step 1: 初始化读取器
    print("\n📥 Step 1: 初始化数据读取器...")
    try:
        reader = SheetDataReader(sheet_id, use_oauth=True)
    except Exception as e:
        result['message'] = f"初始化读取器失败: {e}"
        return result

    # Step 2: 读取PRD数据
    print(f"\n📥 Step 2: 读取PRD数据 [{prd_sheet}]...")
    prd_data = reader.read_sheet(sheet_name=prd_sheet)
    if not prd_data:
        result['message'] = "PRD数据读取失败或为空"
        return result
    print(f"   ✅ 读取 {len(prd_data)} 行PRD数据")

    # Step 3: 读取配置表（可选）
    config_data = None
    if config_sheet:
        print(f"\n📥 Step 3: 读取配置表 [{config_sheet}]...")
        config_data = reader.read_sheet(sheet_name=config_sheet)
        if config_data:
            print(f"   ✅ 读取 {len(config_data)} 行配置数据")
        else:
            print("   ⚠️ 配置表数据为空，跳过配置分析")

    # Step 4: 配置分析
    config_analysis = None
    if config_data:
        print("\n🔍 Step 4: 分析配置表结构...")
        analyzer = ConfigAnalyzer()
        config_analysis = analyzer.analyze_config_structure(config_data)
        print(f"   ✅ 分析完成: {config_analysis['total_fields']} 个字段")

        # 提取边界值
        boundary_tests = []
        for field_info in config_analysis.get('fields', []):
            if field_info.get('datatype') == 'INT' or field_info.get('value_type') == 'NUMBER':
                boundary = analyzer.extract_boundary_values(config_data, field_info['name'])
                if 'error' not in boundary:
                    boundary_tests.append(boundary)

        if boundary_tests:
            print(f"   ✅ 提取 {len(boundary_tests)} 个数值字段的边界值")

    # Step 5: 提取测试要点
    print(f"\n📋 Step 5: 提取测试要点{' (使用 Gemini)' if use_gemini else ''}...")
    extractor = TestPointExtractor()
    report = extractor.extract_from_prd(prd_data, use_gemini=use_gemini)

    # 如果有配置数据，添加配置验证点
    if config_data:
        config_verification = extractor.extract_from_config(config_data)
        for vp in config_verification.get('verification_points', []):
            for checkpoint in vp.get('checkpoints', []):
                report.test_points.append(TestPoint(
                    module='配置验证',
                    checkpoint=vp['field'],
                    priority='P1',
                    category='数值',
                    description=checkpoint,
                    config_ref=vp['field']
                ))

    print(f"   ✅ 提取 {len(report.test_points)} 个测试要点")
    print(f"   功能类型: {report.function_type} → 使用类型: {func_type}")
    print(f"   风险区域: {len(report.risk_areas)} 个")

    # Step 6: 生成测试用例
    print(f"\n📝 Step 6: 生成测试用例 [Type {func_type}]...")
    generator = CaseGenerator(case_prefix=case_prefix)
    cases = generator.generate_cases(report.test_points, func_type)
    print(f"   ✅ 生成 {len(cases)} 条测试用例")

    result['case_count'] = len(cases)

    # Step 7: 输出
    print(f"\n📤 Step 7: 输出结果 [{output_format}]...")

    if output_format == 'markdown':
        output_content = generator.generate_markdown(cases, f"{report.function_name} 测试用例")
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f"   ✅ 已保存到: {output_path}")
        result['output'] = output_content

    elif output_format == 'json':
        output_content = json.dumps(
            generator.format_for_sheets(cases),
            ensure_ascii=False,
            indent=2
        )
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f"   ✅ 已保存到: {output_path}")
        result['output'] = output_content

    elif output_format == 'sheets':
        # 写入Google Sheets
        if output_folder and file_name:
            try:
                from sheets_writer import create_and_write
                formatted_cases = generator.format_for_sheets(cases)
                file_id = create_and_write(
                    folder_url=output_folder,
                    file_name=file_name,
                    test_cases=formatted_cases,
                    sheet_name="用例"
                )
                if file_id:
                    result['output'] = f"https://docs.google.com/spreadsheets/d/{file_id}"
                    print(f"   ✅ 已写入Google Sheets: {result['output']}")
                else:
                    print("   ❌ 写入Google Sheets失败")
            except ImportError:
                print("   ⚠️ sheets_writer模块未找到，改用JSON输出")
                output_format = 'json'
                result['output'] = json.dumps(generator.format_for_sheets(cases), ensure_ascii=False, indent=2)
        else:
            print("   ⚠️ 未指定output_folder或file_name，改用JSON输出")
            result['output'] = json.dumps(generator.format_for_sheets(cases), ensure_ascii=False, indent=2)

    result['success'] = True
    result['message'] = f"成功生成 {len(cases)} 条测试用例"

    # 打印统计
    print("\n" + "="*60)
    print("📊 生成统计")
    print("="*60)
    p0 = sum(1 for c in cases if c.priority == 'P0')
    p1 = sum(1 for c in cases if c.priority == 'P1')
    p2 = sum(1 for c in cases if c.priority == 'P2')
    print(f"   P0 (必测): {p0} 条")
    print(f"   P1 (应测): {p1} 条")
    print(f"   P2 (选测): {p2} 条")
    print(f"   总计: {len(cases)} 条")

    return result


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='SLG 测试用例生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成Markdown格式用例
  python generate_cases.py --sheet-id "xxx" --prd-sheet "推币机PRD" --type D --output cases.md

  # 生成JSON格式用例
  python generate_cases.py --sheet-id "xxx" --prd-sheet "PRD" --config-sheet "配置表" --format json

  # 写入Google Sheets
  python generate_cases.py --sheet-id "xxx" --prd-sheet "PRD" --format sheets \\
    --output-folder "https://drive.google.com/drive/folders/xxx" --file-name "0.85.0_AI_功能名"
        """
    )

    parser.add_argument('--sheet-id', required=True, help='Google Sheets 文档ID')
    parser.add_argument('--prd-sheet', required=True, help='PRD工作表名称')
    parser.add_argument('--config-sheet', help='配置表工作表名称（可选）')
    parser.add_argument('--type', choices=['A', 'B', 'C', 'D'], default='D',
                        help='功能类型: A=新系统, B=功能优化, C=礼包, D=活动（默认D）')
    parser.add_argument('--prefix', default='TC', help='用例编号前缀（默认TC）')
    parser.add_argument('--format', choices=['markdown', 'json', 'sheets'], default='markdown',
                        help='输出格式（默认markdown）')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--output-folder', help='Google Drive 文件夹URL（用于sheets格式）')
    parser.add_argument('--file-name', help='输出文件名（用于sheets格式）')
    parser.add_argument('--use-gemini', action='store_true',
                        help='使用 Gemini 智能解析非结构化文档（需设置 GEMINI_API_KEY 环境变量）')

    args = parser.parse_args()

    print_banner()

    result = generate_test_cases(
        sheet_id=args.sheet_id,
        prd_sheet=args.prd_sheet,
        config_sheet=args.config_sheet,
        func_type=args.type,
        case_prefix=args.prefix,
        output_format=args.format,
        output_path=args.output,
        output_folder=args.output_folder,
        file_name=args.file_name,
        use_gemini=args.use_gemini
    )

    if result['success']:
        print(f"\n✅ {result['message']}")
        if not args.output and args.format in ['markdown', 'json']:
            print("\n" + "="*60)
            print("📄 输出内容")
            print("="*60)
            print(result['output'][:2000])
            if len(result['output']) > 2000:
                print(f"\n... (共 {len(result['output'])} 字符，使用 --output 保存完整内容)")
    else:
        print(f"\n❌ {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
