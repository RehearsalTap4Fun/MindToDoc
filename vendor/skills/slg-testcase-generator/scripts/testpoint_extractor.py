#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试点提取器
功能：从PRD/配置表提取测试要点
支持多种文档格式，可选 Gemini 智能解析
"""
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

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
from document_parser import DocumentParser, ParsedRequirement, DocumentFormat, parse_sheet_data


@dataclass
class TestPoint:
    """测试要点"""
    module: str  # 所属模块
    checkpoint: str  # 检查点
    priority: str  # 优先级 P0/P1/P2
    category: str  # 分类：功能/数值/异常/兼容性
    description: str  # 描述
    config_ref: str = ""  # 关联配置
    risk_level: str = ""  # 风险等级


@dataclass
class TestPointReport:
    """测试要点报告"""
    function_name: str  # 功能名称
    function_type: str  # 功能类型: A/B/C/D
    test_points: List[TestPoint] = field(default_factory=list)
    config_tables: List[Dict[str, str]] = field(default_factory=list)
    risk_areas: List[str] = field(default_factory=list)


class TestPointExtractor:
    """测试点提取器"""

    # 功能类型定义
    FUNCTION_TYPES = {
        'A': {'name': '新系统/新玩法', 'focus': ['完整流程', '状态机', '边界条件', '异常场景']},
        'B': {'name': '原功能优化', 'focus': ['改动点', '兼容性', '回归测试']},
        'C': {'name': '运营礼包', 'focus': ['价格显示', '限购逻辑', '购买流程', '到账验证']},
        'D': {'name': '运营活动', 'focus': ['时间控制', '活动规则', '奖励发放', '活动结束处理']},
    }

    # 高风险场景关键词（基于 slg_rules.md）
    RISK_KEYWORDS = {
        '资产': ['资源', '消耗', '扣除', '奖励', '道具', '货币', '钻石', '金币'],
        '时间': ['跨天', '重置', '倒计时', 'UTC', '到期', '过期'],
        '网络': ['断线', '弱网', '重连', '超时', '请求'],
        '状态': ['状态', '切换', '互斥', '冲突', '条件'],
        '付费': ['付费', '购买', '充值', '限购', '价格', '订单'],
        '跨服': ['跨服', 'KVK', '银河战争', '同步', '数据'],
    }

    # 标准测试模块（按执行顺序）
    STANDARD_MODULES = [
        '活动配置',
        '入口显示',
        '主界面',
        '核心功能',
        '活动结束',
        '跨服数据',
        '兼容性',
        '异常场景',
        '本地化',
    ]

    def __init__(self, sheet_id: str = None):
        """
        初始化提取器

        Args:
            sheet_id: Google Sheets 文档ID
        """
        self.sheet_id = sheet_id
        self.reader = None
        if sheet_id:
            self.reader = SheetDataReader(sheet_id, use_oauth=True)

    def identify_function_type(self, prd_data: List[Dict[str, Any]]) -> str:
        """
        识别功能类型

        Args:
            prd_data: PRD数据

        Returns:
            功能类型代码 A/B/C/D
        """
        # 将所有文本合并进行分析
        all_text = ' '.join(str(v) for row in prd_data for v in row.values())
        text_lower = all_text.lower()

        # 关键词匹配
        type_scores = {'A': 0, 'B': 0, 'C': 0, 'D': 0}

        # Type D: 运营活动
        activity_keywords = ['活动', '限时', '开启时间', '结束时间', '活动奖励', '活动配置']
        for kw in activity_keywords:
            if kw in all_text:
                type_scores['D'] += 1

        # Type C: 运营礼包
        iap_keywords = ['礼包', '付费', '购买', '限购', '充值', '价格', '折扣']
        for kw in iap_keywords:
            if kw in all_text:
                type_scores['C'] += 1

        # Type B: 功能优化
        update_keywords = ['优化', '改进', '修复', '调整', '升级', '迭代']
        for kw in update_keywords:
            if kw in all_text:
                type_scores['B'] += 1

        # Type A: 新系统（默认，如果其他都不明显）
        new_keywords = ['新增', '新功能', '新系统', '新玩法', '全新']
        for kw in new_keywords:
            if kw in all_text:
                type_scores['A'] += 1

        # 返回得分最高的类型，默认为 A
        max_type = max(type_scores, key=type_scores.get)
        if type_scores[max_type] == 0:
            return 'A'
        return max_type

    def identify_risk_areas(self, data: List[Dict[str, Any]]) -> List[str]:
        """
        识别风险区域

        Args:
            data: 数据

        Returns:
            风险区域列表
        """
        all_text = ' '.join(str(v) for row in data for v in row.values())
        risks = []

        for risk_category, keywords in self.RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in all_text:
                    risks.append(f"{risk_category}相关: 涉及{keyword}操作")
                    break

        return risks

    def extract_from_prd(
        self,
        prd_data: List[Dict[str, Any]],
        use_gemini: bool = False
    ) -> TestPointReport:
        """
        从PRD提取测试要点（支持多种文档格式）

        Args:
            prd_data: PRD数据
            use_gemini: 是否使用 Gemini 智能解析

        Returns:
            测试要点报告
        """
        if not prd_data:
            return TestPointReport(
                function_name="未知功能",
                function_type="A",
                test_points=[],
                risk_areas=["数据为空"]
            )

        # 使用文档解析器自动识别格式并提取需求
        doc_format, requirements = parse_sheet_data(prd_data, use_gemini=use_gemini)

        # 识别功能类型
        func_type = self.identify_function_type(prd_data)
        func_info = self.FUNCTION_TYPES[func_type]

        # 尝试提取功能名称
        function_name = self._extract_function_name(prd_data)

        # 识别风险区域
        risk_areas = self.identify_risk_areas(prd_data)

        # 提取测试要点
        test_points = []

        # 从解析的需求生成测试点
        if requirements:
            for req in requirements:
                # 为每个需求生成测试点
                test_points.extend(self._convert_requirement_to_testpoints(req))

        # 如果没有从需求中提取到测试点，使用基于功能类型的标准测试点
        if not test_points:
            for focus in func_info['focus']:
                test_points.append(TestPoint(
                    module='核心功能',
                    checkpoint=focus,
                    priority='P0',
                    category='功能',
                    description=f'验证{focus}的完整性和正确性'
                ))

        # 基于风险区域生成测试点
        for risk in risk_areas:
            test_points.append(TestPoint(
                module='风险验证',
                checkpoint=risk.split(':')[0],
                priority='P0',
                category='异常',
                description=risk,
                risk_level='高'
            ))

        # 添加通用测试点
        common_points = self._generate_common_testpoints(func_type)
        test_points.extend(common_points)

        return TestPointReport(
            function_name=function_name,
            function_type=func_type,
            test_points=test_points,
            risk_areas=risk_areas
        )

    def _convert_requirement_to_testpoints(
        self,
        req: ParsedRequirement
    ) -> List[TestPoint]:
        """
        将解析的需求转换为测试点
        支持新旧两种格式

        Args:
            req: 解析的需求

        Returns:
            测试点列表
        """
        test_points = []

        # 判断是否为新格式（有 trigger_condition 或 operation）
        is_new_format = bool(req.trigger_condition or req.operation)

        if is_new_format:
            # 新格式：使用具体的条件、操作、预期
            # 生成更具体的 checkpoint 名称
            checkpoint = req.feature
            if req.trigger_condition and len(req.trigger_condition) < 30:
                # 将条件包含在 checkpoint 中，使名称更具体
                checkpoint = f"{req.feature}"

            # 构建详细描述
            desc_parts = []
            if req.trigger_condition:
                desc_parts.append(f"前置条件: {req.trigger_condition}")
            if req.operation:
                desc_parts.append(f"操作: {req.operation}")
            if req.expected_result:
                desc_parts.append(f"预期: {req.expected_result}")
            if req.ui_text:
                desc_parts.append(f"显示文案: \"{req.ui_text}\"")

            description = " → ".join(desc_parts) if desc_parts else req.description

            test_points.append(TestPoint(
                module=req.module,
                checkpoint=checkpoint,
                priority=req.priority,
                category='功能',
                description=description[:300],
                config_ref=', '.join(req.config_refs) if req.config_refs else "",
                # 额外信息存储在 remarks 或通过其他方式传递
            ))
        else:
            # 旧格式：使用 description
            test_points.append(TestPoint(
                module=req.module,
                checkpoint=req.feature or "功能验证",
                priority=req.priority,
                category='功能',
                description=req.description[:200] if req.description else f"验证{req.feature}",
                config_ref=', '.join(req.config_refs) if req.config_refs else ""
            ))

        # 如果描述中包含数值，添加边界测试点（仅旧格式）
        desc_to_check = req.description or ''
        numbers = re.findall(r'\d+', desc_to_check)
        if numbers and len(numbers) >= 2 and not is_new_format:
            test_points.append(TestPoint(
                module=req.module,
                checkpoint=f"{req.feature}-边界",
                priority='P1',
                category='数值',
                description=f"验证数值边界条件（涉及数值: {', '.join(numbers[:5])}）",
                config_ref=', '.join(req.config_refs) if req.config_refs else ""
            ))

        # 如果有配置引用，添加配置验证点
        if req.config_refs:
            test_points.append(TestPoint(
                module=req.module,
                checkpoint=f"{req.feature}-配置",
                priority='P1',
                category='配置',
                description=f"验证配置与需求一致（配置: {', '.join(req.config_refs)}）",
                config_ref=', '.join(req.config_refs)
            ))

        return test_points

    def extract_from_config(
        self,
        config_data: List[Dict[str, Any]],
        config_type: str = "activity"
    ) -> Dict[str, Any]:
        """
        从配置表提取验证点

        Args:
            config_data: 配置表数据
            config_type: 配置类型

        Returns:
            验证点字典
        """
        if not config_data:
            return {'error': '配置数据为空'}

        headers = list(config_data[0].keys())
        verification_points = []

        # 分析每个字段生成验证点
        for header in headers:
            field_lower = header.lower()

            # 数值字段
            if any(x in field_lower for x in ['_int_', 'count', 'num', 'limit', 'level']):
                values = [row.get(header) for row in config_data if row.get(header)]
                if values:
                    verification_points.append({
                        'field': header,
                        'type': '数值验证',
                        'checkpoints': [
                            f'验证{header}字段数值正确显示',
                            f'验证边界值处理（最小值、最大值）',
                        ]
                    })

            # 时间字段
            if any(x in field_lower for x in ['time', 'start', 'end', 'date']):
                verification_points.append({
                    'field': header,
                    'type': '时间验证',
                    'checkpoints': [
                        f'验证{header}时间配置与需求一致',
                        '验证时间边界（开始前、进行中、结束后）',
                        '验证跨天重置逻辑',
                    ]
                })

            # 奖励字段
            if any(x in field_lower for x in ['reward', 'award', 'prize', 'gift']):
                verification_points.append({
                    'field': header,
                    'type': '奖励验证',
                    'checkpoints': [
                        f'验证{header}奖励内容与配置一致',
                        '验证奖励发放正确到账',
                        '验证奖励数量计算正确',
                    ]
                })

            # 条件字段
            if any(x in field_lower for x in ['filter', 'condition', 'require', 'unlock']):
                verification_points.append({
                    'field': header,
                    'type': '条件验证',
                    'checkpoints': [
                        f'验证{header}条件判断正确',
                        '验证条件不满足时的提示',
                        '验证条件边界值',
                    ]
                })

        return {
            'config_type': config_type,
            'total_fields': len(headers),
            'verification_points': verification_points,
            'headers': headers
        }

    def _extract_function_name(self, prd_data: List[Dict[str, Any]]) -> str:
        """提取功能名称"""
        # 尝试从常见字段提取
        name_fields = ['功能名称', '活动名称', '名称', 'name', 'title', '标题']

        for row in prd_data[:5]:  # 只检查前5行
            for field in name_fields:
                if field in row and row[field]:
                    return str(row[field])

        # 尝试从第一行的值提取
        if prd_data:
            first_row = prd_data[0]
            for val in first_row.values():
                if val and isinstance(val, str) and len(val) < 50:
                    return val

        return "未命名功能"

    def _generate_common_testpoints(self, func_type: str) -> List[TestPoint]:
        """生成通用测试点"""
        common = []

        # 入口测试点
        common.append(TestPoint(
            module='入口显示',
            checkpoint='入口可见性',
            priority='P0',
            category='功能',
            description='验证入口在正确条件下显示/隐藏'
        ))

        common.append(TestPoint(
            module='入口显示',
            checkpoint='红点逻辑',
            priority='P1',
            category='功能',
            description='验证红点显示和消除条件'
        ))

        # 异常场景测试点
        common.append(TestPoint(
            module='异常场景',
            checkpoint='断线重连',
            priority='P0',
            category='异常',
            description='验证操作过程中断线重连后数据正确'
        ))

        common.append(TestPoint(
            module='异常场景',
            checkpoint='快速连点',
            priority='P0',
            category='异常',
            description='验证按钮防重复点击保护'
        ))

        # 本地化测试点
        common.append(TestPoint(
            module='本地化',
            checkpoint='多语言显示',
            priority='P1',
            category='兼容性',
            description='验证所有文本多语言显示正确'
        ))

        # 活动特有测试点
        if func_type == 'D':
            common.extend([
                TestPoint(
                    module='活动配置',
                    checkpoint='开启机制',
                    priority='P0',
                    category='功能',
                    description='验证活动开启机制（定时/循环/后台/条件触发）'
                ),
                TestPoint(
                    module='活动结束',
                    checkpoint='入口消失',
                    priority='P0',
                    category='功能',
                    description='验证活动结束后入口正确消失'
                ),
                TestPoint(
                    module='活动结束',
                    checkpoint='道具回收',
                    priority='P0',
                    category='功能',
                    description='验证活动道具按配置正确回收'
                ),
            ])

        # 礼包特有测试点
        if func_type == 'C':
            common.extend([
                TestPoint(
                    module='购买流程',
                    checkpoint='价格显示',
                    priority='P0',
                    category='功能',
                    description='验证礼包价格显示与配置一致'
                ),
                TestPoint(
                    module='购买流程',
                    checkpoint='限购逻辑',
                    priority='P0',
                    category='功能',
                    description='验证限购次数和售罄状态'
                ),
                TestPoint(
                    module='购买流程',
                    checkpoint='到账验证',
                    priority='P0',
                    category='功能',
                    description='验证购买后奖励正确到账'
                ),
            ])

        return common

    def generate_report(self, report: TestPointReport) -> str:
        """
        生成Markdown格式报告

        Args:
            report: 测试要点报告

        Returns:
            Markdown字符串
        """
        func_info = self.FUNCTION_TYPES.get(report.function_type, {})

        lines = [
            f"# {report.function_name} - 测试要点报告\n",
            f"## 基本信息\n",
            f"- **功能类型**: {report.function_type} - {func_info.get('name', '未知')}",
            f"- **测试重点**: {', '.join(func_info.get('focus', []))}",
            f"- **测试点数量**: {len(report.test_points)}\n",
        ]

        # 风险区域
        if report.risk_areas:
            lines.append("## 风险区域\n")
            for risk in report.risk_areas:
                lines.append(f"- ⚠️ {risk}")
            lines.append("")

        # 按模块分组测试点
        modules = {}
        for tp in report.test_points:
            if tp.module not in modules:
                modules[tp.module] = []
            modules[tp.module].append(tp)

        lines.append("## 测试要点清单\n")
        for module, points in modules.items():
            lines.append(f"### {module}\n")
            for i, tp in enumerate(points, 1):
                priority_icon = {'P0': '🔴', 'P1': '🟡', 'P2': '🟢'}.get(tp.priority, '⚪')
                lines.append(f"{i}. {priority_icon} **{tp.checkpoint}** [{tp.priority}]")
                lines.append(f"   - {tp.description}")
                if tp.config_ref:
                    lines.append(f"   - 配置引用: {tp.config_ref}")
            lines.append("")

        # 统计
        p0_count = sum(1 for tp in report.test_points if tp.priority == 'P0')
        p1_count = sum(1 for tp in report.test_points if tp.priority == 'P1')
        p2_count = sum(1 for tp in report.test_points if tp.priority == 'P2')

        lines.append("## 统计\n")
        lines.append(f"| 优先级 | 数量 | 占比 |")
        lines.append(f"|--------|------|------|")
        total = len(report.test_points)
        if total > 0:
            lines.append(f"| P0 | {p0_count} | {p0_count*100//total}% |")
            lines.append(f"| P1 | {p1_count} | {p1_count*100//total}% |")
            lines.append(f"| P2 | {p2_count} | {p2_count*100//total}% |")

        return '\n'.join(lines)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='测试点提取器')
    parser.add_argument('--sheet-id', required=True, help='Google Sheets 文档ID')
    parser.add_argument('--prd-sheet', required=True, help='PRD工作表名称')
    parser.add_argument('--config-sheet', help='配置表工作表名称（可选）')
    parser.add_argument('--output', help='输出文件路径')

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("📋 测试点提取器")
    print(f"{'='*60}\n")

    # 初始化提取器
    extractor = TestPointExtractor(args.sheet_id)

    if extractor.reader:
        # 读取PRD数据
        print(f"📥 读取PRD: {args.prd_sheet}")
        prd_data = extractor.reader.read_sheet(sheet_name=args.prd_sheet)

        if prd_data:
            # 提取测试要点
            report = extractor.extract_from_prd(prd_data)

            # 如果有配置表，也进行分析
            if args.config_sheet:
                print(f"📥 读取配置表: {args.config_sheet}")
                config_data = extractor.reader.read_sheet(sheet_name=args.config_sheet)
                if config_data:
                    config_analysis = extractor.extract_from_config(config_data)
                    # 将配置验证点添加到报告
                    for vp in config_analysis.get('verification_points', []):
                        for checkpoint in vp.get('checkpoints', []):
                            report.test_points.append(TestPoint(
                                module='配置验证',
                                checkpoint=vp['field'],
                                priority='P1',
                                category='数值',
                                description=checkpoint,
                                config_ref=vp['field']
                            ))

            # 生成报告
            report_text = extractor.generate_report(report)

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                print(f"\n✅ 报告已保存到: {args.output}")
            else:
                print(report_text)
        else:
            print("❌ 未读取到PRD数据")
    else:
        print("❌ 无法初始化读取器")


if __name__ == "__main__":
    main()
