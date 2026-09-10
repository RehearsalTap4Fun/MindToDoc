#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置表分析器
功能：配置表结构分析、数值验证、边界值提取
"""
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Windows 编码修复（安全版本，避免重复配置）
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    import codecs
    if not isinstance(sys.stdout, codecs.StreamWriter):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')

# 添加脚本目录到 path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from excel_tool import SheetDataReader


class ConfigAnalyzer:
    """配置表分析器"""

    # 字段命名规则
    FIELD_PATTERNS = {
        'endpoint': r'^([ASC])_',  # A=全端, S=服务器, C=客户端
        'datatype': r'^[ASC]_(INT|STR|MAP|ARR)_',  # 数据类型
    }

    # 常见字段及其测试关注点
    FIELD_TEST_FOCUS = {
        'id': '唯一性、引用关系',
        'filter': '解锁条件、前置要求、边界值',
        'components': '功能组件列表、类型覆盖',
        'reward': '奖励配置、数值验证',
        'cost': '消耗配置、资源边界',
        'price': '价格配置、货币验证',
        'limit': '上限配置、边界值',
        'probability': '概率配置、总和验证',
        'time': '时间配置、跨天验证',
        'level': '等级配置、解锁条件',
    }

    def __init__(self, sheet_id: str = None):
        """
        初始化分析器

        Args:
            sheet_id: Google Sheets 文档ID
        """
        self.sheet_id = sheet_id
        self.reader = None
        if sheet_id:
            self.reader = SheetDataReader(sheet_id, use_oauth=True)

    def identify_field_type(self, field_name: str) -> Dict[str, str]:
        """
        识别字段类型

        Args:
            field_name: 字段名称

        Returns:
            字段类型信息 {'endpoint': 'A/S/C', 'datatype': 'INT/STR/MAP/ARR', 'name': '字段名'}
        """
        result = {'endpoint': '', 'datatype': '', 'name': field_name, 'test_focus': ''}

        # 识别端标识
        endpoint_match = re.match(self.FIELD_PATTERNS['endpoint'], field_name)
        if endpoint_match:
            endpoint_map = {'A': '全端', 'S': '服务器', 'C': '客户端'}
            result['endpoint'] = endpoint_map.get(endpoint_match.group(1), '')

        # 识别数据类型
        datatype_match = re.match(self.FIELD_PATTERNS['datatype'], field_name)
        if datatype_match:
            result['datatype'] = datatype_match.group(1)

        # 识别测试关注点
        field_lower = field_name.lower()
        for key, focus in self.FIELD_TEST_FOCUS.items():
            if key in field_lower:
                result['test_focus'] = focus
                break

        return result

    def analyze_config_structure(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析配置表结构

        Args:
            data: 配置表数据列表

        Returns:
            结构分析结果
        """
        if not data:
            return {'error': '数据为空'}

        # 获取表头
        headers = list(data[0].keys())

        # 分析每个字段
        field_analysis = []
        for header in headers:
            field_info = self.identify_field_type(header)

            # 统计该字段的值分布
            values = [row.get(header, '') for row in data]
            non_empty = [v for v in values if v != '' and v is not None]

            field_info['total_rows'] = len(data)
            field_info['non_empty_rows'] = len(non_empty)
            field_info['empty_rows'] = len(data) - len(non_empty)

            # 尝试识别值类型
            if non_empty:
                sample = non_empty[0]
                if isinstance(sample, str):
                    if sample.startswith('{') or sample.startswith('['):
                        field_info['value_type'] = 'JSON'
                    else:
                        field_info['value_type'] = 'STRING'
                elif isinstance(sample, (int, float)):
                    field_info['value_type'] = 'NUMBER'
                else:
                    field_info['value_type'] = 'UNKNOWN'

            field_analysis.append(field_info)

        # 按端标识分组
        by_endpoint = {'全端': [], '服务器': [], '客户端': [], '未知': []}
        for field in field_analysis:
            endpoint = field.get('endpoint', '') or '未知'
            by_endpoint[endpoint].append(field['name'])

        return {
            'total_fields': len(headers),
            'total_rows': len(data),
            'fields': field_analysis,
            'by_endpoint': by_endpoint,
            'headers': headers
        }

    def validate_probability_sum(
        self,
        config_list: List[Dict[str, Any]],
        prob_field: str = "概率"
    ) -> Dict[str, Any]:
        """
        验证概率总和

        Args:
            config_list: 配置列表
            prob_field: 概率字段名

        Returns:
            验证结果
        """
        if not config_list:
            return {'valid': False, 'error': '配置列表为空'}

        total = 0
        details = []

        for i, item in enumerate(config_list):
            prob_value = item.get(prob_field, 0)
            try:
                prob = float(prob_value) if prob_value else 0
                total += prob
                details.append({
                    'index': i,
                    'value': prob,
                    'raw': prob_value
                })
            except (ValueError, TypeError):
                return {
                    'valid': False,
                    'error': f'第{i+1}行概率值无效: {prob_value}'
                }

        # 判断总和是否为100或1（支持百分比和小数两种格式）
        is_valid = abs(total - 100) < 0.01 or abs(total - 1) < 0.001

        return {
            'valid': is_valid,
            'total': total,
            'expected': '100（百分比）或 1（小数）',
            'details': details,
            'test_suggestion': '验证概率总和为100%' if not is_valid else None
        }

    def validate_number_range(
        self,
        value: Any,
        min_val: float,
        max_val: float
    ) -> Dict[str, Any]:
        """
        验证数值范围

        Args:
            value: 要验证的值
            min_val: 最小值
            max_val: 最大值

        Returns:
            验证结果
        """
        try:
            num = float(value)
            in_range = min_val <= num <= max_val

            return {
                'valid': in_range,
                'value': num,
                'min': min_val,
                'max': max_val,
                'boundary_tests': [
                    {'case': f'值为{min_val-1}', 'expected': '不通过（低于下限）'},
                    {'case': f'值为{min_val}', 'expected': '通过（下限边界）'},
                    {'case': f'值为{max_val}', 'expected': '通过（上限边界）'},
                    {'case': f'值为{max_val+1}', 'expected': '不通过（超过上限）'},
                ]
            }
        except (ValueError, TypeError):
            return {
                'valid': False,
                'error': f'无法转换为数值: {value}'
            }

    def extract_boundary_values(
        self,
        data: List[Dict[str, Any]],
        field_name: str
    ) -> Dict[str, Any]:
        """
        提取边界值

        Args:
            data: 配置数据
            field_name: 字段名

        Returns:
            边界值分析结果
        """
        if not data:
            return {'error': '数据为空'}

        values = []
        for row in data:
            val = row.get(field_name)
            if val is not None and val != '':
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass

        if not values:
            return {
                'field': field_name,
                'error': '无有效数值'
            }

        min_val = min(values)
        max_val = max(values)
        unique_vals = sorted(set(values))

        return {
            'field': field_name,
            'min': min_val,
            'max': max_val,
            'count': len(values),
            'unique_count': len(unique_vals),
            'unique_values': unique_vals[:20] if len(unique_vals) <= 20 else unique_vals[:10] + ['...'] + unique_vals[-10:],
            'test_cases': [
                {'boundary': '最小值', 'value': min_val, 'test': f'测试{field_name}={min_val}'},
                {'boundary': '最小值-1', 'value': min_val - 1, 'test': f'测试{field_name}={min_val-1}（低于最小值）'},
                {'boundary': '最大值', 'value': max_val, 'test': f'测试{field_name}={max_val}'},
                {'boundary': '最大值+1', 'value': max_val + 1, 'test': f'测试{field_name}={max_val+1}（超过最大值）'},
            ]
        }

    def parse_json_field(self, value: str) -> Tuple[Any, Optional[str]]:
        """
        解析JSON字段

        Args:
            value: JSON字符串

        Returns:
            (解析结果, 错误信息)
        """
        if not value or not isinstance(value, str):
            return None, '值为空或非字符串'

        try:
            return json.loads(value), None
        except json.JSONDecodeError as e:
            return None, f'JSON解析失败: {e}'

    def analyze_filter_field(self, filter_value: str) -> Dict[str, Any]:
        """
        分析 filter 字段（解锁条件）

        Args:
            filter_value: filter字段的JSON字符串

        Returns:
            分析结果
        """
        parsed, error = self.parse_json_field(filter_value)
        if error:
            return {'error': error}

        # 解析filter结构
        op_map = {
            'ge': '大于等于',
            'gt': '大于',
            'le': '小于等于',
            'lt': '小于',
            'eq': '等于',
            'ne': '不等于',
        }

        typ_map = {
            'building': '建筑等级',
            'level': '玩家等级',
            'vip': 'VIP等级',
            'quest': '任务完成',
        }

        result = {
            'raw': filter_value,
            'parsed': parsed,
            'analysis': {},
            'test_cases': []
        }

        if isinstance(parsed, dict):
            op = parsed.get('op', '')
            typ = parsed.get('typ', '')
            val = parsed.get('val', 0)

            result['analysis'] = {
                'operator': op_map.get(op, op),
                'type': typ_map.get(typ, typ),
                'threshold': val
            }

            # 生成测试用例建议
            if op in ['ge', 'gt']:
                result['test_cases'] = [
                    f'{typ_map.get(typ, typ)}为{val-1}时，不满足条件',
                    f'{typ_map.get(typ, typ)}为{val}时，{"刚好满足" if op == "ge" else "不满足"}条件',
                    f'{typ_map.get(typ, typ)}为{val+1}时，满足条件',
                ]

        return result

    def generate_report(self, data: List[Dict[str, Any]], config_name: str = "配置表") -> str:
        """
        生成配置分析报告

        Args:
            data: 配置数据
            config_name: 配置表名称

        Returns:
            Markdown格式的报告
        """
        structure = self.analyze_config_structure(data)

        report = [
            f"# {config_name} 分析报告\n",
            f"## 概览\n",
            f"- 总字段数: {structure['total_fields']}",
            f"- 总行数: {structure['total_rows']}\n",
            f"## 字段分布\n",
        ]

        # 按端标识分组
        for endpoint, fields in structure['by_endpoint'].items():
            if fields:
                report.append(f"### {endpoint}字段 ({len(fields)}个)")
                report.append("```")
                report.extend(fields[:10])
                if len(fields) > 10:
                    report.append(f"... 共{len(fields)}个")
                report.append("```\n")

        # 需要关注的字段
        report.append("## 测试关注点\n")
        for field in structure['fields']:
            if field.get('test_focus'):
                report.append(f"- **{field['name']}**: {field['test_focus']}")

        return '\n'.join(report)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='配置表分析器')
    parser.add_argument('--sheet-id', required=True, help='Google Sheets 文档ID')
    parser.add_argument('--sheet-name', required=True, help='工作表名称')
    parser.add_argument('--output', help='输出文件路径')

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("🔍 配置表分析器")
    print(f"{'='*60}\n")

    # 初始化分析器
    analyzer = ConfigAnalyzer(args.sheet_id)

    # 读取数据
    if analyzer.reader:
        data = analyzer.reader.read_sheet(sheet_name=args.sheet_name)

        if data:
            # 生成报告
            report = analyzer.generate_report(data, args.sheet_name)

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"✅ 报告已保存到: {args.output}")
            else:
                print(report)

            # 分析边界值
            print("\n## 数值字段边界值分析\n")
            structure = analyzer.analyze_config_structure(data)
            for field in structure['fields']:
                if field.get('datatype') == 'INT' or field.get('value_type') == 'NUMBER':
                    boundary = analyzer.extract_boundary_values(data, field['name'])
                    if 'error' not in boundary:
                        print(f"### {field['name']}")
                        print(f"- 最小值: {boundary['min']}")
                        print(f"- 最大值: {boundary['max']}")
                        print(f"- 唯一值数量: {boundary['unique_count']}\n")
        else:
            print("❌ 未读取到数据")
    else:
        print("❌ 无法初始化读取器")


if __name__ == "__main__":
    main()
