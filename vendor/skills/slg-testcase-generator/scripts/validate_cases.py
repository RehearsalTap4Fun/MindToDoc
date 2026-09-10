#!/usr/bin/env python3
"""
用例格式校验脚本

校验 AI 生成的用例 JSON 文件，检查：
1. 格式完整性（每行6列、空值占位）
2. 检查点密度（仅1条会提示建议合并、>15条会提示建议拆分）
3. 硬编码数值检测（配置可调的数值不应写死）
4. 合并标记一致性（""空字符串标记是否正确）

用法:
    python scripts/validate_cases.py test_cases.json
    python scripts/validate_cases.py test_cases.json --strict
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path


class CaseValidator:
    COLUMNS = ["编号", "功能模块", "检查点", "操作步骤", "预期结果", "备注"]

    HARDCODE_PATTERNS = [
        (r'\$\d+\.?\d*', '价格硬编码（应写"价格与配置一致"）'),
        (r'(?<!\w)\d{4,}(?:元|金币|钻石|宝石)', '大数值硬编码（应写"与配置一致"）'),
        (r'(?:概率|几率)\s*(?:为|是|=)\s*\d+\.?\d*%', '概率硬编码（应写"概率与配置一致"）'),
        (r'(?:CD|冷却|间隔)\s*(?:为|是|=)\s*\d+\s*[秒分时]', '时间硬编码（应写"与配置一致"）'),
        (r'(?:上限|次数|限购)\s*(?:为|是|=)\s*\d+\s*次', '次数硬编码（应写"与配置一致"）'),
    ]

    # 允许的数值模式（不应误报）
    SAFE_PATTERNS = [
        r'n[+-]\d',        # n-1, n+1
        r'第n',            # 第n天
        r'与配置一致',
        r'配置表\w+',
        r'见\d{4}',        # 见2011（配置表ID）
    ]

    def __init__(self, strict=False):
        self.strict = strict
        self.errors = []
        self.warnings = []

    def validate_file(self, filepath: str) -> bool:
        path = Path(filepath)
        if not path.exists():
            self.errors.append(f"文件不存在: {filepath}")
            return False

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON 解析失败: {e}")
            return False

        if not isinstance(data, list):
            self.errors.append("数据格式错误：顶层必须是数组")
            return False

        self._check_structure(data)
        self._check_checkpoint_granularity(data)
        self._check_merge_markers(data)
        self._check_hardcoded_values(data)

        return len(self.errors) == 0

    def _check_structure(self, data: list):
        for i, row in enumerate(data):
            row_num = i + 1
            if not isinstance(row, list):
                self.errors.append(f"第{row_num}行：不是数组格式（当前为 {type(row).__name__}）")
                continue
            if len(row) != 6:
                self.errors.append(f"第{row_num}行：列数为{len(row)}，应为6列")
                continue
            if not row[0]:
                self.errors.append(f"第{row_num}行：编号（A列）不能为空")
            if not row[4] and row[4] != "":
                self.warnings.append(f"第{row_num}行：预期结果（E列）为空，请确认")
            for j, cell in enumerate(row):
                if cell is None:
                    self.errors.append(
                        f"第{row_num}行{self.COLUMNS[j]}列：值为null，空值应用空字符串\"\"")

    def _check_checkpoint_granularity(self, data: list):
        checkpoint_counts = defaultdict(list)
        current_module = ""
        current_checkpoint = ""

        for i, row in enumerate(data):
            if not isinstance(row, list) or len(row) < 3:
                continue
            if row[1]:
                current_module = row[1]
            if row[2]:
                current_checkpoint = row[2]
            key = f"{current_module}|{current_checkpoint}"
            checkpoint_counts[key].append(i + 1)

        for key, rows in checkpoint_counts.items():
            module, checkpoint = key.split("|", 1)
            if len(rows) == 1:
                self.warnings.append(
                    f"检查点过密：「{module}-{checkpoint}」仅有1条用例（第{rows[0]}行），"
                    f"若与相邻检查点属同一验证维度建议合并")
            elif len(rows) > 15:
                self.warnings.append(
                    f"检查点过大：「{module}-{checkpoint}」有{len(rows)}条用例"
                    f"（第{rows[0]}-{rows[-1]}行），建议拆分到15条以内")

        module_counts = defaultdict(list)
        current_module = ""
        for i, row in enumerate(data):
            if not isinstance(row, list) or len(row) < 2:
                continue
            if row[1]:
                current_module = row[1]
            module_counts[current_module].append(i + 1)

        for module, rows in module_counts.items():
            if not module:
                continue
            if module == checkpoint:
                self.warnings.append(
                    f"模块名与检查点名完全一致：「{module}」，检查点应比模块更具体")

    def _check_merge_markers(self, data: list):
        prev_module = None
        prev_checkpoint = None
        prev_step = None

        for i, row in enumerate(data):
            if not isinstance(row, list) or len(row) < 4:
                continue
            row_num = i + 1

            # B列
            if row[1] == "":
                if prev_module is None:
                    self.errors.append(f"第{row_num}行：B列为空但前面没有模块名")
            else:
                prev_module = row[1]
                prev_checkpoint = None
                prev_step = None

            # C列
            if row[2] == "":
                if prev_checkpoint is None and prev_module is not None:
                    pass  # 第一条没写检查点也算合理（虽然不规范）
            else:
                prev_checkpoint = row[2]
                prev_step = None

            # D列
            if row[3] == "":
                pass
            else:
                prev_step = row[3]

    def _check_hardcoded_values(self, data: list):
        for i, row in enumerate(data):
            if not isinstance(row, list) or len(row) < 5:
                continue
            row_num = i + 1
            expected = str(row[4]) if row[4] else ""
            remark = str(row[5]) if len(row) > 5 and row[5] else ""
            text = expected + " " + remark

            if any(re.search(p, text) for p in self.SAFE_PATTERNS):
                continue

            for pattern, desc in self.HARDCODE_PATTERNS:
                match = re.search(pattern, expected)
                if match:
                    if self.strict:
                        self.errors.append(
                            f"第{row_num}行预期结果：{desc} → \"{match.group()}\"")
                    else:
                        self.warnings.append(
                            f"第{row_num}行预期结果：疑似{desc} → \"{match.group()}\"")

    def report(self) -> str:
        lines = []
        if self.errors:
            lines.append(f"\n❌ 错误（{len(self.errors)}个，必须修复）：")
            for err in self.errors:
                lines.append(f"  ✗ {err}")

        if self.warnings:
            lines.append(f"\n⚠️ 警告（{len(self.warnings)}个，建议检查）：")
            for warn in self.warnings:
                lines.append(f"  ⚠ {warn}")

        if not self.errors and not self.warnings:
            lines.append("\n✅ 校验通过，未发现问题")
        elif not self.errors:
            lines.append(f"\n✅ 无致命错误，{len(self.warnings)}个警告")
        else:
            lines.append(f"\n❌ 校验失败：{len(self.errors)}个错误，{len(self.warnings)}个警告")

        return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/validate_cases.py <json文件路径> [--strict]")
        print("  --strict  严格模式：硬编码检测也视为错误")
        sys.exit(1)

    filepath = sys.argv[1]
    strict = "--strict" in sys.argv

    validator = CaseValidator(strict=strict)
    validator.validate_file(filepath)
    print(validator.report())

    sys.exit(1 if validator.errors else 0)


if __name__ == "__main__":
    main()
