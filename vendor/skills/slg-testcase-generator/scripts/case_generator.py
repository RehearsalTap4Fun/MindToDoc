#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例生成器
功能：根据测试点生成结构化测试用例
"""
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

from testpoint_extractor import TestPoint, TestPointReport


@dataclass
class TestCase:
    """测试用例"""
    case_id: str  # 用例编号
    module: str  # 功能模块
    checkpoint: str  # 检查点
    steps: str  # 操作步骤
    expected: str  # 预期结果
    priority: str  # 优先级
    remarks: str = ""  # 备注


class CaseGenerator:
    """测试用例生成器"""

    # 用例编号计数器
    _case_counter: int = 0
    _case_prefix: str = ""

    # 测试方法模板
    BOUNDARY_TEMPLATE = {
        'min': '验证{field}为最小值{min_val}时的表现',
        'min_minus': '验证{field}低于最小值（{min_val}-1）时被拒绝',
        'max': '验证{field}为最大值{max_val}时的表现',
        'max_plus': '验证{field}超过最大值（{max_val}+1）时被拒绝',
    }

    # 等价类模板
    EQUIVALENCE_TEMPLATE = {
        'valid': '验证{field}在有效范围内的表现',
        'invalid': '验证{field}为无效值时的错误处理',
        'empty': '验证{field}为空时的默认处理',
    }

    # 场景模板
    SCENARIO_TEMPLATES = {
        '入口显示': [
            {'steps': '1. 满足解锁条件\n2. 进入相关界面', 'expected': '入口图标正确显示'},
            {'steps': '1. 不满足解锁条件\n2. 进入相关界面', 'expected': '入口不显示或置灰'},
        ],
        '红点逻辑': [
            {'steps': '1. 存在可领取内容\n2. 查看入口', 'expected': '红点显示'},
            {'steps': '1. 领取所有内容\n2. 查看入口', 'expected': '红点消失'},
        ],
        '断线重连': [
            {'steps': '1. 开始操作\n2. 操作过程中断网\n3. 重连', 'expected': '数据与服务器一致，无异常'},
        ],
        '快速连点': [
            {'steps': '1. 快速连续点击按钮', 'expected': '只执行一次操作，无重复扣费'},
        ],
        '跨天重置': [
            {'steps': '1. 跨天前有进度\n2. 等待跨天\n3. 检查数据', 'expected': '数据按规则重置'},
        ],
    }

    # UI/视觉验证模板
    UI_TEMPLATES = {
        '按钮状态': [
            {'checkpoint': '按钮正常状态', 'steps': '1. 满足操作条件\n2. 查看按钮', 'expected': '按钮高亮可点击，文字清晰'},
            {'checkpoint': '按钮禁用状态', 'steps': '1. 不满足条件（资源不足/次数用尽）\n2. 查看按钮', 'expected': '按钮置灰，显示不可点击原因'},
            {'checkpoint': '按钮点击反馈', 'steps': '1. 点击可用按钮', 'expected': '按钮有按下缩放/变色动效'},
        ],
        '品质颜色': [
            {'checkpoint': '蓝色品质显示', 'steps': '1. 查看蓝色品质物品', 'expected': '边框/背景为蓝色(#3498db)，品质图标正确'},
            {'checkpoint': '紫色品质显示', 'steps': '1. 查看紫色品质物品', 'expected': '边框/背景为紫色(#9b59b6)，品质图标正确'},
            {'checkpoint': '橙色品质显示', 'steps': '1. 查看橙色品质物品', 'expected': '边框/背景为橙色(#e67e22)，品质图标正确'},
            {'checkpoint': '红色品质显示', 'steps': '1. 查看红色品质物品', 'expected': '边框/背景为红色(#e74c3c)，品质图标正确'},
        ],
        '数量显示': [
            {'checkpoint': '数量充足显示', 'steps': '1. 当前数量>=需求数量\n2. 查看数量文本', 'expected': '数量显示白色/绿色，无警告'},
            {'checkpoint': '数量不足显示', 'steps': '1. 当前数量<需求数量\n2. 查看数量文本', 'expected': '数量显示红色，提示不足'},
        ],
        '进度条': [
            {'checkpoint': '进度条初始状态', 'steps': '1. 新开始活动\n2. 查看进度条', 'expected': '进度条为0%，起始位置'},
            {'checkpoint': '进度条更新', 'steps': '1. 完成部分进度\n2. 查看进度条', 'expected': '进度条按比例填充，有动效'},
            {'checkpoint': '进度条满值', 'steps': '1. 完成全部进度\n2. 查看进度条', 'expected': '进度条100%满，显示完成状态'},
        ],
        '图标状态': [
            {'checkpoint': '未解锁图标', 'steps': '1. 查看未解锁内容', 'expected': '图标灰色/带锁标记'},
            {'checkpoint': '已解锁图标', 'steps': '1. 解锁内容\n2. 查看图标', 'expected': '图标彩色，无锁标记'},
            {'checkpoint': '已获得图标', 'steps': '1. 获得物品\n2. 查看图标', 'expected': '显示"已拥有"角标或勾选'},
        ],
    }

    # 动效验证模板
    ANIMATION_TEMPLATES = {
        '获得动效': [
            {'checkpoint': '获得物品动效', 'steps': '1. 获得物品/奖励', 'expected': '播放获得特效，物品飞入背包'},
            {'checkpoint': '获得货币动效', 'steps': '1. 获得货币', 'expected': '货币图标飞向顶部资源栏，数字跳动增加'},
        ],
        '消耗动效': [
            {'checkpoint': '消耗确认弹窗', 'steps': '1. 点击消耗按钮', 'expected': '弹出确认窗口，显示消耗数量'},
            {'checkpoint': '消耗扣除动效', 'steps': '1. 确认消耗', 'expected': '资源数字跳动减少，有扣除音效'},
        ],
        '界面转场': [
            {'checkpoint': '界面打开动效', 'steps': '1. 点击入口打开界面', 'expected': '界面有淡入/缩放出现动效'},
            {'checkpoint': '界面关闭动效', 'steps': '1. 点击关闭按钮', 'expected': '界面有淡出/缩放消失动效'},
        ],
        '抽奖动效': [
            {'checkpoint': '抽奖过程动效', 'steps': '1. 点击抽奖按钮', 'expected': '播放抽奖动画（转盘/开箱等）'},
            {'checkpoint': '抽奖结果展示', 'steps': '1. 抽奖完成', 'expected': '结果物品高亮展示，有获得特效'},
        ],
    }

    # 购买流程详细模板
    PURCHASE_FLOW_TEMPLATES = {
        '价格显示': [
            {'checkpoint': '原价显示', 'steps': '1. 查看礼包价格', 'expected': '显示原价，货币符号正确'},
            {'checkpoint': '折扣价显示', 'steps': '1. 有折扣时查看价格', 'expected': '原价划线，折扣价高亮，折扣标签正确'},
        ],
        '购买按钮': [
            {'checkpoint': '可购买状态', 'steps': '1. 有购买次数\n2. 查看购买按钮', 'expected': '按钮显示价格，可点击'},
            {'checkpoint': '已售罄状态', 'steps': '1. 购买次数用尽\n2. 查看按钮', 'expected': '按钮显示"售罄"，不可点击'},
        ],
        '限购提示': [
            {'checkpoint': '限购次数显示', 'steps': '1. 查看限购商品', 'expected': '显示"限购X次"或"剩余X次"'},
            {'checkpoint': '限购倒计时', 'steps': '1. 限时限购商品', 'expected': '显示重置倒计时'},
        ],
        '购买确认': [
            {'checkpoint': '确认弹窗内容', 'steps': '1. 点击购买按钮', 'expected': '弹窗显示商品名、价格、数量'},
            {'checkpoint': '取消购买', 'steps': '1. 点击确认弹窗外/取消', 'expected': '弹窗关闭，不扣费'},
            {'checkpoint': '确认购买', 'steps': '1. 点击确认按钮', 'expected': '调起支付/扣除货币'},
        ],
        '购买结果': [
            {'checkpoint': '购买成功', 'steps': '1. 支付成功', 'expected': '提示购买成功，奖励到账，次数-1'},
            {'checkpoint': '购买失败', 'steps': '1. 支付失败/取消', 'expected': '提示失败原因，不扣费不发货'},
        ],
    }

    # 活动专用模板（Type D）- v2增强版
    ACTIVITY_TEMPLATES = {
        '活动配置': [
            {'checkpoint': '配置验证', 'steps': '读取活动配置表S_MAP_start_trigger字段', 'expected': '开启机制配置正确'},
            {'checkpoint': '解锁配置', 'steps': '读取功能解锁配置', 'expected': '解锁条件配置正确'},
        ],
        '入口显示': [
            {'checkpoint': 'HUD入口显示', 'steps': '1. 满足解锁条件\n2. 活动期间查看主界面', 'expected': '活动入口hud正确显示'},
            {'checkpoint': 'HUD样式检查', 'steps': '查看入口hud', 'expected': 'hud样式符合需求（图标、位置、大小）'},
            {'checkpoint': '入口红点数字', 'steps': '1. 存在可领取内容/免费次数\n2. 查看入口', 'expected': '红点显示具体数字'},
            {'checkpoint': '入口倒计时显示', 'steps': '1. 活动存在倒计时状态\n2. 查看入口', 'expected': '倒计时正确显示，数值同配置'},
        ],
        '入口状态切换': [
            {'checkpoint': '倒计时→血条切换', 'steps': '1. 等待倒计时结束\n2. 目标出现\n3. 检查入口', 'expected': '入口从倒计时切换为血条/进度显示'},
            {'checkpoint': '血条→倒计时切换', 'steps': '1. 目标被击杀/消失\n2. 进入刷新期\n3. 检查入口', 'expected': '入口从血条切换为倒计时显示'},
            {'checkpoint': '状态切换间隔', 'steps': '等待配置的切换间隔时间后检查入口状态', 'expected': '状态按配置间隔切换'},
        ],
        '入口血条状态': [
            {'checkpoint': '血条满值显示', 'steps': '1. 目标满血/进度0\n2. 查看入口', 'expected': '血条100%，显示绿色'},
            {'checkpoint': '血条黄色状态', 'steps': '1. 100%>血量/进度>20%\n2. 查看入口', 'expected': '血条填充颜色为黄色'},
            {'checkpoint': '血条红色状态', 'steps': '1. 血量/进度≤20%\n2. 查看入口', 'expected': '血条填充颜色为红色'},
        ],
        '活动结束': [
            {'checkpoint': '入口消失', 'steps': '1. 活动结束\n2. 查看主界面', 'expected': '活动入口消失'},
            {'checkpoint': '道具回收', 'steps': '1. 活动结束\n2. 检查活动道具', 'expected': '活动道具按配置回收'},
            {'checkpoint': '邮件发放', 'steps': '1. 活动结束有未使用道具\n2. 检查邮箱', 'expected': '收到回收邮件'},
        ],
    }

    # 多人互动场景模板
    MULTIPLAYER_TEMPLATES = {
        '数据同步': [
            {'checkpoint': '血条实时刷新', 'steps': '1. A玩家攻击目标\n2. B玩家在主界面查看入口血条', 'expected': '血条实时刷新，显示最新血量'},
            {'checkpoint': '排行榜实时更新', 'steps': '1. A玩家获得积分\n2. B玩家查看排行榜', 'expected': '排行榜数据实时更新'},
            {'checkpoint': '进度实时同步', 'steps': '1. A玩家完成操作增加全服进度\n2. B玩家查看进度', 'expected': '进度实时同步'},
        ],
        '并发操作': [
            {'checkpoint': '多人同时操作', 'steps': '多个玩家同时进行操作', 'expected': '各自数据正确，无冲突'},
        ],
    }

    # 状态刷新/重置模板
    STATE_REFRESH_TEMPLATES = {
        '刷新等待期': [
            {'checkpoint': '击杀后等待期', 'steps': '1. 目标被击杀\n2. 检查界面状态', 'expected': '显示刷新倒计时，等待新目标'},
            {'checkpoint': '逃跑/消失后等待期', 'steps': '1. 目标逃跑/消失\n2. 检查界面状态', 'expected': '显示刷新倒计时，等待新目标'},
            {'checkpoint': '新目标刷新', 'steps': '1. 等待刷新倒计时结束\n2. 检查界面', 'expected': '新目标出现，状态重置'},
        ],
        '多轮次刷新': [
            {'checkpoint': '多轮目标刷新', 'steps': '1. 完成多轮操作\n2. 检查每轮状态', 'expected': '每轮状态正确刷新'},
        ],
        '跨天重置': [
            {'checkpoint': '跨天数据重置', 'steps': '1. 跨越UTC0点\n2. 检查免费次数/进度', 'expected': '数据按配置重置'},
            {'checkpoint': '跨天排行榜', 'steps': '1. 跨越UTC0点\n2. 检查排行榜', 'expected': '排行榜按配置重置或保留'},
        ],
    }

    # 礼包专用模板（Type C）
    IAP_TEMPLATES = {
        '礼包显示': [
            {'checkpoint': '价格显示', 'steps': '1. 进入礼包界面\n2. 查看价格', 'expected': '价格与配置一致'},
            {'checkpoint': '奖励预览', 'steps': '查看礼包奖励内容', 'expected': '奖励内容与配置一致'},
        ],
        '购买流程': [
            {'checkpoint': '正常购买', 'steps': '1. 选择礼包\n2. 确认购买\n3. 完成支付', 'expected': '奖励正确到账'},
            {'checkpoint': '取消购买', 'steps': '1. 选择礼包\n2. 取消购买', 'expected': '不扣费不发货'},
            {'checkpoint': '连点购买', 'steps': '快速连续点击购买按钮', 'expected': '只购买1次'},
        ],
        '限购逻辑': [
            {'checkpoint': '限购1次', 'steps': '1. 购买礼包\n2. 查看礼包状态', 'expected': '显示"售罄"或消失'},
            {'checkpoint': '限购多次', 'steps': '1. 购买1次\n2. 查看剩余次数', 'expected': '限购次数-1'},
        ],
    }

    def __init__(self, case_prefix: str = "TC"):
        """
        初始化生成器

        Args:
            case_prefix: 用例编号前缀
        """
        self._case_prefix = case_prefix
        self._case_counter = 0

    def _next_case_id(self) -> str:
        """生成下一个用例编号"""
        self._case_counter += 1
        return f"{self._case_prefix}_{self._case_counter:03d}"

    def generate_cases(
        self,
        test_points: List[TestPoint],
        func_type: str = "A"
    ) -> List[TestCase]:
        """
        根据测试点生成用例

        Args:
            test_points: 测试点列表
            func_type: 功能类型 A/B/C/D

        Returns:
            测试用例列表
        """
        cases = []
        # 用于去重：记录已生成的 (module, checkpoint, steps_hash)
        seen_cases = set()

        for tp in test_points:
            generated = self._generate_smart_case(tp)
            for case in generated:
                # 生成唯一标识用于去重
                case_key = (case.module, case.checkpoint, hash(case.steps))
                if case_key not in seen_cases:
                    seen_cases.add(case_key)
                    cases.append(case)

        # 添加功能类型特定用例
        if func_type == 'D':
            for case in self._generate_activity_cases():
                case_key = (case.module, case.checkpoint, hash(case.steps))
                if case_key not in seen_cases:
                    seen_cases.add(case_key)
                    cases.append(case)
        elif func_type == 'C':
            for case in self._generate_iap_cases():
                case_key = (case.module, case.checkpoint, hash(case.steps))
                if case_key not in seen_cases:
                    seen_cases.add(case_key)
                    cases.append(case)

        # 添加通用异常场景（只添加一次）
        for case in self._generate_common_exception_cases():
            case_key = (case.module, case.checkpoint, hash(case.steps))
            if case_key not in seen_cases:
                seen_cases.add(case_key)
                cases.append(case)

        return cases

    def _generate_smart_case(self, tp: TestPoint) -> List[TestCase]:
        """
        智能生成测试用例，根据测试点内容匹配最佳模板

        Args:
            tp: 测试点

        Returns:
            测试用例列表
        """
        text = f"{tp.checkpoint} {tp.description}".lower()

        # 判断是否已经是原子化的具体测试点（包含具体数值或明确行为）
        is_atomic = self._is_atomic_testpoint(tp)

        # 1. 优先匹配场景模板（但只用于通用场景）
        if tp.checkpoint in self.SCENARIO_TEMPLATES and not is_atomic:
            cases = []
            for template in self.SCENARIO_TEMPLATES[tp.checkpoint]:
                cases.append(TestCase(
                    case_id=self._next_case_id(),
                    module=tp.module,
                    checkpoint=tp.checkpoint,
                    steps=template['steps'],
                    expected=template['expected'],
                    priority=tp.priority,
                    remarks=tp.category
                ))
            return cases

        # 如果是原子化测试点，直接生成单个具体用例
        if is_atomic:
            return self._generate_atomic_case(tp)

        # 2. 检测数值验证关键词（优先于UI模板）
        if any(kw in text for kw in ['概率', '几率', '比例', '%']):
            return self._generate_probability_case(tp)

        if any(kw in text for kw in ['单价', '消耗量']) and not any(kw in text for kw in ['按钮', '购买']):
            return self._generate_value_case(tp)

        # 3. 检测购买相关关键词（比UI模板更具体）
        if any(kw in text for kw in ['购买', '礼包']) and '按钮' not in text:
            return self._apply_template(tp, self.PURCHASE_FLOW_TEMPLATES.get('购买确认', []))

        if any(kw in text for kw in ['限购', '售罄']):
            return self._apply_template(tp, self.PURCHASE_FLOW_TEMPLATES.get('限购提示', []))

        # 4. 检测特定UI场景（只在没有更具体的上下文时使用）
        if '按钮' in text and not any(kw in text for kw in ['购买', '礼包', '确认', '取消']):
            return self._apply_template(tp, self.UI_TEMPLATES.get('按钮状态', []))

        if any(kw in text for kw in ['图鉴', '解锁']) and '概率' not in text:
            return self._apply_template(tp, self.UI_TEMPLATES.get('图标状态', []))

        # 5. 检测动效相关关键词
        if any(kw in text for kw in ['获得', '奖励', '领取']) and '概率' not in text:
            return self._apply_template(tp, self.ANIMATION_TEMPLATES.get('获得动效', []))

        if any(kw in text for kw in ['消耗', '扣除', '花费']) and '数量' not in text:
            return self._apply_template(tp, self.ANIMATION_TEMPLATES.get('消耗动效', []))

        # 6. 默认生成 - 改进版
        return self._generate_default_case(tp)

    def _is_atomic_testpoint(self, tp: TestPoint) -> bool:
        """
        判断测试点是否已经是原子化的
        原子化测试点特征：包含具体数值、明确的条件、单一验证点
        """
        import re
        text = f"{tp.checkpoint} {tp.description}"

        # 包含具体数值（如 70%、5%、1级）
        has_number = bool(re.search(r'\d+[%％级次条个]', text))

        # 包含具体等级/品质说明
        has_specific = any(kw in text for kw in [
            '1级', '2级', '3级', '4级', '5级', '6级', '7级', '8级',
            '蓝色鱼', '紫色鱼', '橙色鱼', '红色鱼',
            '蓝色订单', '紫色订单', '橙色订单'
        ])

        # 描述长度适中（太短可能是概括性的，太长可能是多个验证点）
        is_moderate_length = 10 <= len(text) <= 100

        return (has_number or has_specific) and is_moderate_length

    def _generate_atomic_case(self, tp: TestPoint) -> List[TestCase]:
        """
        生成原子化测试用例（保留原始描述的具体内容）
        """
        # 从描述中提取操作步骤
        steps = self._extract_atomic_steps(tp)
        expected = self._extract_atomic_expected(tp)

        return [TestCase(
            case_id=self._next_case_id(),
            module=tp.module,
            checkpoint=tp.checkpoint,
            steps=steps,
            expected=expected,
            priority=tp.priority,
            remarks=tp.category
        )]

    def _extract_atomic_steps(self, tp: TestPoint) -> str:
        """从原子化测试点提取操作步骤"""
        import re
        text = f"{tp.checkpoint} {tp.description}"

        # 提取等级信息
        level_match = re.search(r'(\d+)级', text)
        level = level_match.group(1) if level_match else ""

        # 根据内容类型生成步骤
        if '概率' in text or '几率' in text:
            if level:
                return f"1. 设置钓鱼等级为{level}级\n2. 进行多次钓鱼操作（100次以上）\n3. 统计各品质鱼的出现次数"
            return f"1. 进行多次相关操作（100次以上）\n2. 统计各结果出现次数\n3. 计算实际概率"

        if '消耗' in text:
            return f"1. 记录当前资源数量\n2. 执行{tp.checkpoint}操作\n3. 检查资源变化"

        if '奖励' in text or '获得' in text:
            return f"1. 满足{tp.checkpoint}条件\n2. 执行领取/获得操作\n3. 检查奖励到账"

        if '显示' in text:
            return f"1. 进入相关界面\n2. 查看{tp.checkpoint}\n3. 对比显示内容与配置"

        # 默认
        return f"1. 进入{tp.module}界面\n2. 执行{tp.checkpoint}相关操作\n3. 验证结果"

    def _extract_atomic_expected(self, tp: TestPoint) -> str:
        """从原子化测试点提取预期结果"""
        import re
        text = tp.description

        # 如果描述已经包含具体数值，直接使用
        numbers = re.findall(r'\d+[%％]', text)
        if numbers:
            return f"{tp.checkpoint}：{text}"

        # 如果描述是"验证xxx与配置相符"格式
        if '配置' in text:
            return f"{tp.checkpoint}与配置表数值一致"

        # 默认
        return f"{tp.checkpoint}功能正常：{text}"

    def _apply_template(self, tp: TestPoint, templates: List[Dict]) -> List[TestCase]:
        """应用模板生成用例"""
        cases = []
        for template in templates:
            cases.append(TestCase(
                case_id=self._next_case_id(),
                module=tp.module,
                checkpoint=template.get('checkpoint', tp.checkpoint),
                steps=template['steps'],
                expected=template['expected'],
                priority=tp.priority,
                remarks=tp.category
            ))
        return cases

    def _generate_probability_case(self, tp: TestPoint) -> List[TestCase]:
        """生成概率验证用例"""
        return [TestCase(
            case_id=self._next_case_id(),
            module=tp.module,
            checkpoint=tp.checkpoint,
            steps=f"1. 准备测试数据\n2. 执行{tp.checkpoint}操作100次以上\n3. 记录各结果出现次数",
            expected=f"{tp.description}，实际概率与配置偏差不超过5%",
            priority=tp.priority,
            remarks="概率验证"
        )]

    def _generate_value_case(self, tp: TestPoint) -> List[TestCase]:
        """生成数值验证用例"""
        return [TestCase(
            case_id=self._next_case_id(),
            module=tp.module,
            checkpoint=tp.checkpoint,
            steps=f"1. 查看{tp.checkpoint}配置表\n2. 在游戏中触发相关操作\n3. 对比实际数值与配置",
            expected=f"{tp.description}，数值与配置表一致",
            priority=tp.priority,
            remarks="数值验证"
        )]

    def _generate_default_case(self, tp: TestPoint) -> List[TestCase]:
        """
        改进的默认用例生成
        支持新格式（含条件、操作、预期）和旧格式
        """
        desc = tp.description

        # 检测是否为新格式（包含 "前置条件:" 或 "操作:" 或 "预期:"）
        is_new_format = any(marker in desc for marker in ['前置条件:', '操作:', '预期:', '显示文案:'])

        if is_new_format:
            # 新格式：解析结构化描述
            steps, expected = self._parse_structured_description(desc, tp.checkpoint)
        else:
            # 旧格式：尝试从描述中提取
            steps = self._extract_steps(desc, tp.checkpoint)
            expected = self._extract_expected(desc, tp.checkpoint)

        return [TestCase(
            case_id=self._next_case_id(),
            module=tp.module,
            checkpoint=tp.checkpoint,
            steps=steps,
            expected=expected,
            priority=tp.priority,
            remarks=tp.category
        )]

    def _parse_structured_description(self, desc: str, checkpoint: str) -> tuple:
        """
        解析结构化描述（新格式）
        格式: "前置条件: xxx → 操作: xxx → 预期: xxx → 显示文案: xxx"
        """
        import re

        # 提取各部分
        condition_match = re.search(r'前置条件:\s*([^→]+)', desc)
        operation_match = re.search(r'操作:\s*([^→]+)', desc)
        expected_match = re.search(r'预期:\s*([^→]+)', desc)
        ui_text_match = re.search(r'显示文案:\s*"([^"]+)"', desc)

        # 构建操作步骤
        steps_parts = []
        if condition_match:
            condition = condition_match.group(1).strip()
            steps_parts.append(f"1. {condition}")
        if operation_match:
            operation = operation_match.group(1).strip()
            step_num = len(steps_parts) + 1
            steps_parts.append(f"{step_num}. {operation}")

        if not steps_parts:
            steps_parts.append(f"1. 进入{checkpoint}相关界面")
            steps_parts.append("2. 执行相关操作")

        steps = "\n".join(steps_parts)

        # 构建预期结果
        expected_parts = []
        if expected_match:
            expected_parts.append(expected_match.group(1).strip())
        if ui_text_match:
            ui_text = ui_text_match.group(1).strip()
            expected_parts.append(f"显示文案: \"{ui_text}\"")

        if expected_parts:
            expected = "，".join(expected_parts)
        else:
            expected = f"{checkpoint}功能正常"

        return steps, expected

    def _extract_steps(self, desc: str, checkpoint: str) -> str:
        """从描述中提取操作步骤"""
        # 如果描述已经包含步骤格式
        if '1.' in desc or '1、' in desc:
            return desc.replace('1、', '1. ').replace('2、', '2. ').replace('3、', '3. ')

        # 根据关键词生成步骤
        if '验证' in desc:
            target = desc.replace('验证', '').strip()
            return f"1. 进入相关界面\n2. 查看{checkpoint}\n3. 对比{target}"

        if '检查' in desc:
            target = desc.replace('检查', '').strip()
            return f"1. 触发相关条件\n2. 查看{target}"

        # 默认步骤
        return f"1. 进入{checkpoint}相关界面\n2. 执行相关操作\n3. 检查结果"

    def _extract_expected(self, desc: str, checkpoint: str) -> str:
        """从描述中提取预期结果"""
        # 如果描述包含具体数值
        import re
        numbers = re.findall(r'\d+[%％]?', desc)
        if numbers:
            return f"{checkpoint}显示正确：{', '.join(numbers)}"

        # 如果描述包含状态词
        if any(kw in desc for kw in ['正确', '成功', '显示', '出现']):
            return f"{desc.split('验证')[-1].strip() if '验证' in desc else desc}"

        # 默认预期
        return f"{checkpoint}功能正常，符合设计预期"

    def _generate_common_exception_cases(self) -> List[TestCase]:
        """生成通用异常场景用例"""
        exception_cases = [
            {
                'module': '异常场景',
                'checkpoint': '断线重连',
                'steps': '1. 开始操作\n2. 操作过程中断网\n3. 重连',
                'expected': '数据与服务器一致，无异常',
                'priority': 'P0'
            },
            {
                'module': '异常场景',
                'checkpoint': '快速连点',
                'steps': '1. 快速连续点击按钮',
                'expected': '只执行一次操作，无重复扣费',
                'priority': 'P0'
            },
            {
                'module': '本地化',
                'checkpoint': '多语言显示',
                'steps': '1. 验证所有文本多语言显示正确',
                'expected': '验证通过：验证所有文本多语言显示正确',
                'priority': 'P1'
            },
        ]

        return [
            TestCase(
                case_id=self._next_case_id(),
                module=ec['module'],
                checkpoint=ec['checkpoint'],
                steps=ec['steps'],
                expected=ec['expected'],
                priority=ec['priority'],
                remarks='通用场景'
            )
            for ec in exception_cases
        ]

    def _generate_activity_cases(self) -> List[TestCase]:
        """生成活动专用用例（包含多人互动和状态刷新场景）"""
        cases = []

        # 活动基础模板
        for module, templates in self.ACTIVITY_TEMPLATES.items():
            for template in templates:
                cases.append(TestCase(
                    case_id=self._next_case_id(),
                    module=module,
                    checkpoint=template['checkpoint'],
                    steps=template['steps'],
                    expected=template['expected'],
                    priority='P0',
                    remarks='活动专用'
                ))

        # 多人互动场景
        for module, templates in self.MULTIPLAYER_TEMPLATES.items():
            for template in templates:
                cases.append(TestCase(
                    case_id=self._next_case_id(),
                    module=f"多人互动-{module}",
                    checkpoint=template['checkpoint'],
                    steps=template['steps'],
                    expected=template['expected'],
                    priority='P1',
                    remarks='多人场景'
                ))

        # 状态刷新场景
        for module, templates in self.STATE_REFRESH_TEMPLATES.items():
            for template in templates:
                cases.append(TestCase(
                    case_id=self._next_case_id(),
                    module=f"状态刷新-{module}",
                    checkpoint=template['checkpoint'],
                    steps=template['steps'],
                    expected=template['expected'],
                    priority='P1',
                    remarks='状态刷新'
                ))

        return cases

    def _generate_iap_cases(self) -> List[TestCase]:
        """生成礼包专用用例"""
        cases = []
        for module, templates in self.IAP_TEMPLATES.items():
            for template in templates:
                cases.append(TestCase(
                    case_id=self._next_case_id(),
                    module=module,
                    checkpoint=template['checkpoint'],
                    steps=template['steps'],
                    expected=template['expected'],
                    priority='P0',
                    remarks='礼包专用'
                ))
        return cases

    def apply_boundary_method(
        self,
        field_name: str,
        min_val: Any,
        max_val: Any,
        module: str = "数值验证"
    ) -> List[TestCase]:
        """
        应用边界值分析方法

        Args:
            field_name: 字段名
            min_val: 最小值
            max_val: 最大值
            module: 所属模块

        Returns:
            边界值测试用例列表
        """
        cases = []

        boundary_cases = [
            (f'{field_name}最小值', min_val, '正常处理'),
            (f'{field_name}低于最小值', min_val - 1, '拒绝或提示错误'),
            (f'{field_name}最大值', max_val, '正常处理'),
            (f'{field_name}超过最大值', max_val + 1, '拒绝或提示错误'),
        ]

        for checkpoint, value, expected in boundary_cases:
            cases.append(TestCase(
                case_id=self._next_case_id(),
                module=module,
                checkpoint=checkpoint,
                steps=f"1. 设置{field_name}={value}\n2. 执行操作",
                expected=expected,
                priority='P0',
                remarks='边界值测试'
            ))

        return cases

    def apply_equivalence_method(
        self,
        field_name: str,
        valid_values: List[Any],
        invalid_values: List[Any],
        module: str = "等价类验证"
    ) -> List[TestCase]:
        """
        应用等价类划分方法

        Args:
            field_name: 字段名
            valid_values: 有效值列表
            invalid_values: 无效值列表
            module: 所属模块

        Returns:
            等价类测试用例列表
        """
        cases = []

        # 有效等价类
        for val in valid_values[:3]:  # 最多取3个代表
            cases.append(TestCase(
                case_id=self._next_case_id(),
                module=module,
                checkpoint=f'{field_name}有效值',
                steps=f"1. 设置{field_name}={val}\n2. 执行操作",
                expected="操作成功",
                priority='P0',
                remarks='有效等价类'
            ))

        # 无效等价类
        for val in invalid_values[:3]:
            cases.append(TestCase(
                case_id=self._next_case_id(),
                module=module,
                checkpoint=f'{field_name}无效值',
                steps=f"1. 设置{field_name}={val}\n2. 执行操作",
                expected="拒绝操作或提示错误",
                priority='P1',
                remarks='无效等价类'
            ))

        return cases

    def format_for_sheets(self, cases: List[TestCase]) -> List[Dict[str, str]]:
        """
        格式化为Google Sheets写入格式

        按照合并规则：同模块/检查点的后续行留空

        Args:
            cases: 测试用例列表

        Returns:
            格式化的字典列表
        """
        formatted = []
        prev_module = None
        prev_checkpoint = None

        for case in cases:
            row = {
                "编号": case.case_id,
                "模块": case.module if case.module != prev_module else "",
                "检查点": case.checkpoint if case.checkpoint != prev_checkpoint or case.module != prev_module else "",
                "操作步骤": case.steps,
                "预期结果": case.expected,
                "其他": f"{case.priority} {case.remarks}".strip()
            }
            formatted.append(row)

            prev_module = case.module
            prev_checkpoint = case.checkpoint

        return formatted

    def generate_markdown(self, cases: List[TestCase], title: str = "测试用例") -> str:
        """
        生成Markdown格式输出

        Args:
            cases: 测试用例列表
            title: 标题

        Returns:
            Markdown字符串
        """
        lines = [
            f"# {title}\n",
            f"**用例数量**: {len(cases)}\n",
            "| 编号 | 模块 | 检查点 | 操作步骤 | 预期结果 | 优先级 |",
            "|------|------|--------|----------|----------|--------|",
        ]

        for case in cases:
            steps = case.steps.replace('\n', '<br>')
            lines.append(
                f"| {case.case_id} | {case.module} | {case.checkpoint} | "
                f"{steps} | {case.expected} | {case.priority} |"
            )

        # 统计
        p0 = sum(1 for c in cases if c.priority == 'P0')
        p1 = sum(1 for c in cases if c.priority == 'P1')
        p2 = sum(1 for c in cases if c.priority == 'P2')

        lines.extend([
            "",
            "## 统计",
            f"- P0: {p0} 条",
            f"- P1: {p1} 条",
            f"- P2: {p2} 条",
            f"- 总计: {len(cases)} 条",
        ])

        return '\n'.join(lines)


def main():
    """命令行入口"""
    import argparse
    import json

    parser = argparse.ArgumentParser(description='测试用例生成器')
    parser.add_argument('--input', required=True, help='测试点JSON文件或PRD文本')
    parser.add_argument('--type', choices=['A', 'B', 'C', 'D'], default='A', help='功能类型')
    parser.add_argument('--prefix', default='TC', help='用例编号前缀')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--format', choices=['markdown', 'json', 'sheets'], default='markdown', help='输出格式')

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("📝 测试用例生成器")
    print(f"{'='*60}\n")

    # 初始化生成器
    generator = CaseGenerator(case_prefix=args.prefix)

    # 读取测试点
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)

        test_points = [
            TestPoint(
                module=tp.get('module', ''),
                checkpoint=tp.get('checkpoint', ''),
                priority=tp.get('priority', 'P1'),
                category=tp.get('category', ''),
                description=tp.get('description', '')
            )
            for tp in data.get('test_points', [])
        ]
    except (json.JSONDecodeError, FileNotFoundError):
        # 如果不是JSON，创建简单测试点
        test_points = [
            TestPoint(module='核心功能', checkpoint='主流程', priority='P0', category='功能', description='验证主流程'),
        ]

    # 生成用例
    cases = generator.generate_cases(test_points, args.type)

    print(f"✅ 生成 {len(cases)} 条测试用例")

    # 输出
    if args.format == 'markdown':
        output = generator.generate_markdown(cases, f"Type {args.type} 测试用例")
    elif args.format == 'json':
        output = json.dumps(
            [{'case_id': c.case_id, 'module': c.module, 'checkpoint': c.checkpoint,
              'steps': c.steps, 'expected': c.expected, 'priority': c.priority}
             for c in cases],
            ensure_ascii=False, indent=2
        )
    else:  # sheets
        output = json.dumps(generator.format_for_sheets(cases), ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"✅ 已保存到: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
