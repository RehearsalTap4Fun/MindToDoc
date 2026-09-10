#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档解析器 - 支持多种文档格式
自动识别文档结构并提取需求内容
"""
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 注意：Windows 编码问题由主入口脚本处理


class DocumentFormat(Enum):
    """文档格式类型"""
    TABULAR = "tabular"  # 结构化表格（有明确列名）
    DOCUMENT = "document"  # 文档式（合并单元格、非表格）
    MIXED = "mixed"  # 混合格式
    UNKNOWN = "unknown"


@dataclass
class ParsedRequirement:
    """解析出的需求项"""
    module: str  # 模块/功能
    feature: str  # 功能点/场景描述
    description: str  # 详细描述（兼容旧格式）
    priority: str = "P1"  # 优先级
    config_refs: List[str] = None  # 配置引用
    ui_refs: List[str] = None  # UI引用
    source_row: int = 0  # 来源行号
    # 新增字段（v2格式）
    trigger_condition: str = ""  # 触发条件
    operation: str = ""  # 具体操作
    expected_result: str = ""  # 预期结果
    ui_text: str = ""  # UI文案
    flow_sequence: int = 0  # 流程序号

    def __post_init__(self):
        if self.config_refs is None:
            self.config_refs = []
        if self.ui_refs is None:
            self.ui_refs = []
        # 如果有新格式字段，自动生成 description
        if self.trigger_condition or self.operation:
            if not self.description:
                parts = []
                if self.trigger_condition:
                    parts.append(f"条件: {self.trigger_condition}")
                if self.operation:
                    parts.append(f"操作: {self.operation}")
                if self.expected_result:
                    parts.append(f"预期: {self.expected_result}")
                if self.ui_text:
                    parts.append(f"文案: \"{self.ui_text}\"")
                self.description = " | ".join(parts)


class DocumentParser:
    """智能文档解析器"""

    # 识别结构化表格的关键词
    TABULAR_HEADERS = [
        '模块', '功能', '需求', '描述', '检查点', '验收标准',
        'module', 'feature', 'requirement', 'description'
    ]

    # 识别PRD内容的关键词
    PRD_KEYWORDS = [
        '玩法', '规则', '逻辑', '流程', '触发', '条件', '奖励',
        '消耗', '显示', '入口', '界面', '配置', '参数'
    ]

    # 识别配置引用的模式
    CONFIG_PATTERNS = [
        r'(\d{4,})表',  # 2111表, 21121101表
        r'A_INT_\w+',  # A_INT_id
        r'S_MAP_\w+',  # S_MAP_start_trigger
        r'S_LIST_\w+',  # S_LIST_rewards
    ]

    def __init__(self):
        self.gemini_client = None

    def detect_format(self, data: List[Dict[str, Any]]) -> DocumentFormat:
        """
        检测文档格式类型

        Args:
            data: 从 Sheet 读取的数据

        Returns:
            文档格式类型
        """
        if not data:
            return DocumentFormat.UNKNOWN

        # 获取所有非空的列名
        headers = [h for h in data[0].keys() if h and h.strip()]

        # 检查是否有结构化表头
        tabular_score = sum(
            1 for h in headers
            if any(kw in h.lower() for kw in self.TABULAR_HEADERS)
        )

        # 检查数据一致性（每行是否有相同结构）
        non_empty_counts = []
        for row in data[:20]:  # 检查前20行
            count = sum(1 for v in row.values() if v and str(v).strip())
            non_empty_counts.append(count)

        # 计算变异系数（标准差/均值）
        if non_empty_counts:
            avg = sum(non_empty_counts) / len(non_empty_counts)
            if avg > 0:
                variance = sum((x - avg) ** 2 for x in non_empty_counts) / len(non_empty_counts)
                cv = (variance ** 0.5) / avg
            else:
                cv = 1.0
        else:
            cv = 1.0

        # 判断格式
        if tabular_score >= 2 and cv < 0.5:
            return DocumentFormat.TABULAR
        elif tabular_score >= 1 and cv < 0.7:
            return DocumentFormat.MIXED
        else:
            return DocumentFormat.DOCUMENT

    def parse_tabular(self, data: List[Dict[str, Any]]) -> List[ParsedRequirement]:
        """解析结构化表格格式"""
        requirements = []

        # 尝试识别列映射
        column_map = self._identify_columns(data[0].keys() if data else [])

        for idx, row in enumerate(data):
            # 跳过空行
            if not any(str(v).strip() for v in row.values()):
                continue

            req = ParsedRequirement(
                module=str(row.get(column_map.get('module', ''), '')).strip(),
                feature=str(row.get(column_map.get('feature', ''), '')).strip(),
                description=str(row.get(column_map.get('description', ''), '')).strip(),
                source_row=idx + 1
            )

            # 提取配置引用
            full_text = ' '.join(str(v) for v in row.values())
            req.config_refs = self._extract_config_refs(full_text)

            if req.module or req.feature or req.description:
                requirements.append(req)

        return requirements

    def parse_document(self, data: List[Dict[str, Any]]) -> List[ParsedRequirement]:
        """
        解析文档式格式（合并单元格、非表格）
        将连续的内容块组织成需求项
        """
        requirements = []
        current_module = ""
        current_feature = ""
        content_buffer = []

        for idx, row in enumerate(data):
            # 获取该行所有非空内容
            contents = [str(v).strip() for v in row.values() if v and str(v).strip()]

            if not contents:
                # 空行 - 可能是段落分隔
                if content_buffer:
                    req = self._create_requirement_from_buffer(
                        current_module, current_feature, content_buffer, idx
                    )
                    if req:
                        requirements.append(req)
                    content_buffer = []
                continue

            text = ' '.join(contents)

            # 检查是否是模块标题（如 "一、鱼饵"、"## 钓鱼玩法"）
            module_match = re.match(r'^[一二三四五六七八九十\d]+[、.．]\s*(.+)$', text)
            if module_match or text.startswith('#'):
                # 保存之前的内容
                if content_buffer:
                    req = self._create_requirement_from_buffer(
                        current_module, current_feature, content_buffer, idx
                    )
                    if req:
                        requirements.append(req)
                    content_buffer = []

                current_module = module_match.group(1) if module_match else text.lstrip('#').strip()
                current_feature = ""
                continue

            # 检查是否是功能点标题（数字开头或特定格式）
            feature_match = re.match(r'^[\d]+[.)）]\s*(.+)$', text)
            if feature_match:
                if content_buffer:
                    req = self._create_requirement_from_buffer(
                        current_module, current_feature, content_buffer, idx
                    )
                    if req:
                        requirements.append(req)
                    content_buffer = []

                current_feature = feature_match.group(1)
                continue

            # 普通内容行
            content_buffer.append((idx, text))

        # 处理最后的缓冲区
        if content_buffer:
            req = self._create_requirement_from_buffer(
                current_module, current_feature, content_buffer, len(data)
            )
            if req:
                requirements.append(req)

        return requirements

    def parse_with_gemini(
        self,
        data: List[Dict[str, Any]],
        context: str = ""
    ) -> List[ParsedRequirement]:
        """
        使用 Gemini 智能解析非结构化文档

        Args:
            data: Sheet 数据
            context: 额外上下文（如功能名称）

        Returns:
            解析出的需求列表
        """
        if not self.gemini_client:
            self._init_gemini()

        if not self.gemini_client:
            print("⚠️ Gemini 未配置，回退到本地解析")
            return self.parse_document(data)

        # 构建文档文本
        doc_text = self._build_document_text(data)

        # 构建 prompt - 优化版v3：增加入口/HUD、多人互动、状态刷新场景
        prompt = f"""你是一个资深的游戏QA专家，需要从PRD文档中提取**可执行**的测试用例。

## 文档内容
{doc_text[:15000]}

## 核心原则
1. **原子化**: 每个需求只验证**一个**具体场景
2. **条件明确**: 写清楚具体的触发条件（如"鱼饵=0个"而非"资源不足"）
3. **文案提取**: 从PRD中提取具体的提示文案、按钮文字、错误信息
4. **数值具体**: 提取文档中的具体数值（概率、价格、数量、时间间隔）
5. **流程串联**: 相关场景按操作顺序排列
6. **配置引用**: 提取具体的配置表名称和字段

## 输出格式
```json
[
  {{
    "module": "功能模块名",
    "feature": "场景描述（包含具体条件）",
    "trigger_condition": "触发条件（越具体越好）",
    "operation": "具体操作步骤",
    "expected_result": "预期结果（包含UI文案和颜色/动效描述）",
    "ui_text": "界面上显示的具体文案（如有）",
    "priority": "P0/P1/P2",
    "config_refs": ["配置表名_字段名"],
    "flow_sequence": 0
  }}
]
```

## 关键要求

### 1. 条件必须具体
**错误**: "资源不足时点击按钮"
**正确**: "金币数量<100时，点击购买按钮"

### 2. 必须提取UI文案和状态
从PRD中找到所有提示语、状态描述：
- 错误提示："金币不足"、"次数已用完"、"活动已结束"
- 状态描述："血条填充颜色为黄色"、"倒计时显示"、"红点数字+2"
- 按钮文字："确认"、"取消"、"购买"

### 3. 数值和颜色必须具体
从PRD提取所有数值和视觉描述：
- "血量>20%时，血条为黄色"
- "血量≤20%时，血条为红色"
- "等待间隔6秒"
- "概率=70%"

### 4. 配置引用必须具体
提取具体的配置表和字段：
- "1768_x2_chapter_quest_function_unlock"
- "CoinPileNum配置"
- "2182表reward字段"

### 5. 流程必须串联
用 flow_sequence 标记同一流程的步骤顺序。

## 必须覆盖的场景类型

### A. 入口/HUD显示（重点！）
活动入口是测试重点，每个状态单独一条：
- 入口是否显示（解锁前/后，活动期间/结束）
- 入口图标样式
- 入口红点显示和数字
- 入口倒计时显示
- 入口血条/进度显示（颜色变化）
- 入口状态切换（倒计时↔血条↔等待）

### B. 主界面UI细节
- 界面标题文案
- 各按钮位置和状态
- 数值显示位置和格式
- 动效播放

### C. 多人互动场景（重要！）
- A玩家操作后，B玩家界面的实时刷新
- 多人同时操作的数据一致性
- 跨服数据同步

### D. 状态刷新/重置（重要！）
- 怪物被击杀后的刷新等待期表现
- 怪物逃跑后的刷新等待期表现
- 跨天重置后的状态
- 活动结束后的状态

### E. 正向流程（每个步骤单独一条）
- 进入界面 → 操作 → 反馈 → 结果

### F. 异常分支
- 资源不足（具体到每种资源和数量）
- 次数用完
- 条件不满足

### G. 边界条件
- 最小值边界（0、1）
- 最大值边界（满级、上限）
- 阈值切换点（如血量20%是颜色切换点）

## 示例输出

```json
[
  {{
    "module": "活动开启",
    "feature": "检查活动入口HUD显示",
    "trigger_condition": "活动已开启，功能已解锁",
    "operation": "进入游戏主界面",
    "expected_result": "新增独立的活动hud入口",
    "ui_text": "",
    "priority": "P0",
    "config_refs": ["1768_x2_chapter_quest_function_unlock"],
    "flow_sequence": 1
  }},
  {{
    "module": "活动开启",
    "feature": "入口HUD红点检查",
    "trigger_condition": "玩家有免费次数未使用",
    "operation": "查看入口hud",
    "expected_result": "hud显示数字红点",
    "ui_text": "红点数字2",
    "priority": "P1",
    "config_refs": [],
    "flow_sequence": 2
  }},
  {{
    "module": "活动开启",
    "feature": "入口血条黄色状态",
    "trigger_condition": "怪物剩余生命百分比>20%",
    "operation": "查看入口hud",
    "expected_result": "入口血条填充颜色为黄色",
    "ui_text": "",
    "priority": "P1",
    "config_refs": [],
    "flow_sequence": 0
  }},
  {{
    "module": "活动开启",
    "feature": "入口血条红色状态",
    "trigger_condition": "怪物剩余生命百分比≤20%",
    "operation": "查看入口hud",
    "expected_result": "入口血条填充颜色为红色",
    "ui_text": "",
    "priority": "P1",
    "config_refs": [],
    "flow_sequence": 0
  }},
  {{
    "module": "活动开启",
    "feature": "入口血条实时刷新（多人）",
    "trigger_condition": "A玩家正在攻击怪物",
    "operation": "B玩家在游戏主界面查看活动入口血条",
    "expected_result": "入口血条会实时刷新，显示最新血量",
    "ui_text": "",
    "priority": "P1",
    "config_refs": [],
    "flow_sequence": 0
  }},
  {{
    "module": "活动开启",
    "feature": "怪物被击杀后入口显示",
    "trigger_condition": "当前怪物被击杀，进入刷新等待期",
    "operation": "查看入口hud",
    "expected_result": "入口不显示怪物血条，只显示倒计时",
    "ui_text": "",
    "priority": "P1",
    "config_refs": [],
    "flow_sequence": 0
  }}
]
```

## 重要提示
1. **入口测试是重点**: 活动入口/HUD的各种状态是人工测试的重点，务必覆盖
2. **覆盖度优先**: 尽可能多地提取可测试场景
3. **多人场景不能少**: 多人互动、数据同步是常见遗漏点
4. **状态切换要覆盖**: 各种状态的切换点和等待期
5. **视觉细节要具体**: 颜色、动效、样式都要描述

请仔细阅读文档，提取**所有**可测试的场景（目标: 50-80个场景）。
只返回JSON数组。"""

        try:
            # 使用 google.genai 客户端接口
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt
            )
            result_text = response.text

            # 提取 JSON（支持截断修复）
            import json
            parsed = self._parse_json_with_truncation_fix(result_text)
            if parsed:
                print(f"✅ Gemini 成功解析出 {len(parsed)} 个需求项")

                requirements = []
                for item in parsed:
                    # 支持新旧两种格式
                    req = ParsedRequirement(
                        module=item.get('module', ''),
                        feature=item.get('feature', ''),
                        description=item.get('description', ''),  # 旧格式
                        priority=item.get('priority', 'P1'),
                        config_refs=item.get('config_refs', []),
                        # 新格式字段
                        trigger_condition=item.get('trigger_condition', ''),
                        operation=item.get('operation', ''),
                        expected_result=item.get('expected_result', ''),
                        ui_text=item.get('ui_text', ''),
                        flow_sequence=item.get('flow_sequence', 0)
                    )
                    requirements.append(req)

                return requirements
        except Exception as e:
            print(f"⚠️ Gemini 解析失败: {e}")

        return self.parse_document(data)

    def _init_gemini(self):
        """初始化 Gemini 客户端"""
        try:
            from google import genai
            import os
            import json

            # 优先从配置文件读取
            api_key = None
            config_paths = [
                Path(__file__).parent / 'config.json',  # scripts/config.json
                Path(__file__).parent.parent / 'config.json',  # skill/config.json
                Path(__file__).parent.parent.parent.parent / 'config.json',  # qa/config.json
            ]

            for config_path in config_paths:
                if config_path.exists():
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        api_key = config.get('gemini_api_key')
                        if api_key:
                            print(f"✅ 从配置文件读取 Gemini API Key")
                            break
                    except Exception:
                        continue

            # 回退到环境变量
            if not api_key:
                api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

            if api_key:
                self.gemini_client = genai.Client(api_key=api_key)
                self.gemini_model = "gemini-2.0-flash"  # 使用快速模型
                print("✅ Gemini 客户端已初始化")
            else:
                print("⚠️ 未找到 GEMINI_API_KEY，请在 config.json 或环境变量中配置")
        except ImportError:
            print("⚠️ 未安装 google-genai，请运行: pip install google-genai")
        except Exception as e:
            print(f"⚠️ Gemini 初始化失败: {e}")

    def _identify_columns(self, headers: List[str]) -> Dict[str, str]:
        """识别列映射"""
        column_map = {}

        module_keywords = ['模块', '功能模块', 'module']
        feature_keywords = ['功能', '功能点', '需求', 'feature', 'requirement']
        desc_keywords = ['描述', '说明', '详情', 'description', 'detail']

        for header in headers:
            h_lower = header.lower()
            if any(kw in h_lower for kw in module_keywords):
                column_map['module'] = header
            elif any(kw in h_lower for kw in feature_keywords):
                column_map['feature'] = header
            elif any(kw in h_lower for kw in desc_keywords):
                column_map['description'] = header

        return column_map

    def _extract_config_refs(self, text: str) -> List[str]:
        """提取配置引用"""
        refs = []
        for pattern in self.CONFIG_PATTERNS:
            matches = re.findall(pattern, text)
            refs.extend(matches)
        return list(set(refs))

    def _create_requirement_from_buffer(
        self,
        module: str,
        feature: str,
        buffer: List[Tuple[int, str]],
        end_row: int
    ) -> Optional[ParsedRequirement]:
        """从内容缓冲区创建需求项"""
        if not buffer:
            return None

        # 合并描述
        description = '\n'.join(text for _, text in buffer)

        # 如果没有模块名，尝试从内容中提取
        if not module:
            # 使用第一行非空内容作为模块名
            module = buffer[0][1][:20] if buffer else "未分类"

        # 如果没有功能点名，尝试从内容中提取关键词
        if not feature:
            for _, text in buffer:
                for kw in self.PRD_KEYWORDS:
                    if kw in text:
                        feature = text[:30]
                        break
                if feature:
                    break

        # 提取配置引用
        config_refs = self._extract_config_refs(description)

        # 确定优先级
        priority = "P1"
        if any(kw in description for kw in ['必须', '核心', '关键', '资产', '付费', '货币']):
            priority = "P0"
        elif any(kw in description for kw in ['优化', '体验', '建议', '可选']):
            priority = "P2"

        return ParsedRequirement(
            module=module or "未分类",
            feature=feature or "通用功能",
            description=description,
            priority=priority,
            config_refs=config_refs,
            source_row=buffer[0][0] if buffer else end_row
        )

    def _build_document_text(self, data: List[Dict[str, Any]]) -> str:
        """构建文档文本用于 LLM 处理"""
        lines = []
        for row in data:
            contents = [str(v).strip() for v in row.values() if v and str(v).strip()]
            if contents:
                lines.append(' | '.join(contents))
        return '\n'.join(lines)

    def _parse_json_with_truncation_fix(self, text: str) -> List[Dict]:
        """
        解析 JSON，自动修复 Gemini 输出截断问题

        常见问题：
        - Gemini 输出 token 限制导致 JSON 被截断
        - 最后一个对象不完整
        - 缺少结尾的 ]

        Args:
            text: Gemini 返回的文本

        Returns:
            解析出的列表，失败返回空列表
        """
        import json

        # 尝试找到 JSON 数组
        json_match = re.search(r'\[[\s\S]*', text)
        if not json_match:
            return []

        json_str = json_match.group()

        # 尝试 1: 直接解析完整 JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # 尝试 2: 找到最后一个完整的 }, 并补充 ]
        last_complete = json_str.rfind('},')
        if last_complete > 0:
            fixed = json_str[:last_complete+1] + ']'
            try:
                result = json.loads(fixed)
                print(f"⚠️ JSON 被截断，已修复（恢复 {len(result)} 个完整项）")
                return result
            except json.JSONDecodeError:
                pass

        # 尝试 3: 找到最后一个完整的 } 并补充 ]
        last_brace = json_str.rfind('}')
        if last_brace > 0:
            fixed = json_str[:last_brace+1] + ']'
            try:
                result = json.loads(fixed)
                print(f"⚠️ JSON 被截断，已修复（恢复 {len(result)} 个完整项）")
                return result
            except json.JSONDecodeError:
                pass

        # 尝试 4: 逐个尝试截断点
        for i in range(len(json_str) - 1, 0, -1):
            if json_str[i] == '}':
                try:
                    result = json.loads(json_str[:i+1] + ']')
                    print(f"⚠️ JSON 严重截断，恢复了 {len(result)} 个项")
                    return result
                except json.JSONDecodeError:
                    continue

        print("❌ 无法修复截断的 JSON")
        return []


def parse_sheet_data(
    data: List[Dict[str, Any]],
    use_gemini: bool = False
) -> Tuple[DocumentFormat, List[ParsedRequirement]]:
    """
    解析 Sheet 数据的便捷函数

    Args:
        data: 从 Sheet 读取的数据
        use_gemini: 是否使用 Gemini 增强解析

    Returns:
        (文档格式, 需求列表)
    """
    parser = DocumentParser()
    doc_format = parser.detect_format(data)

    print(f"📄 检测到文档格式: {doc_format.value}")

    if doc_format == DocumentFormat.TABULAR:
        requirements = parser.parse_tabular(data)
    elif use_gemini:
        requirements = parser.parse_with_gemini(data)
    else:
        requirements = parser.parse_document(data)

    print(f"📋 提取 {len(requirements)} 个需求项")

    return doc_format, requirements


if __name__ == "__main__":
    # 测试
    test_data = [
        {'一、鱼饵': ''},
        {'一、鱼饵': '鱼饵单价'},
        {'一、鱼饵': '单次钓鱼消耗鱼饵数量'},
        {'一、鱼饵': ''},
        {'一、鱼饵': '二、鱼'},
        {'一、鱼饵': '钓鱼等级'},
    ]

    doc_format, reqs = parse_sheet_data(test_data)
    print(f"\n格式: {doc_format}")
    for req in reqs:
        print(f"- [{req.module}] {req.feature}: {req.description[:50]}...")
