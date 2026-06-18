#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan §11 自检自动化 -- stub 抽提 + 静态符号一致性检查。

用法:
    python scripts/check_plan_signatures.py docs/superpowers/plans/<plan>.md
    python scripts/check_plan_signatures.py <plan>.md --critical TagSpec PatchContext register

行为:
1. 从 plan 抽出所有 ```python``` 代码块;
2. 每段单独 ast.parse 检查语法合法;
3. 收集所有顶层 def / class / 赋值 / import 名字成"已定义集";
4. 校验关键符号(--critical)在已定义集里(若不在 → 报错 + 退出 1);
5. 扫描所有 lib./app./g./mod. 之类属性访问,统计未定义但被引用的;
6. 默认 stdout 简短报告,--verbose 给完整列表;退出码 0/1。

设计原则:
- 无副作用:不写任何文件,不需要 ruff/mypy 安装;
- 容错:future-import 顺序问题在拼接段时跳过,改逐段 parse;
- 输出 utf-8 安全:在 Windows GBK 控制台也不丢 ASCII 报告。
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

DEFAULT_BUILTINS = (
    set(dir(__builtins__)) | {
        "self", "cls", "args", "kwargs",
        # 常见标准库
        "json", "math", "sys", "os", "Path", "dataclass", "field",
        "Callable", "Iterable", "defaultdict",
        # 常见第三方
        "openpyxl", "Workbook", "load_workbook", "argparse",
        "importlib", "pytest", "tmp_path", "monkeypatch",
        # 常见 plan 内部别名
        "lib", "g", "app", "mod",
        "True", "False", "None",
    }
)


def extract_python_blocks(plan_path: Path) -> list[str]:
    content = plan_path.read_text(encoding="utf-8")
    return re.findall(r"```python\n(.*?)```", content, re.DOTALL)


def check_syntax(blocks: list[str]) -> list[str]:
    errors: list[str] = []
    for i, b in enumerate(blocks, 1):
        try:
            ast.parse(b)
        except SyntaxError as e:
            errors.append(f"block {i} L{e.lineno}: {e.msg}")
    return errors


def collect_defined_names(blocks: list[str]) -> set[str]:
    """逐段 ast.parse 收集顶层 def / class / 赋值 / import 名字。"""
    names = set(DEFAULT_BUILTINS)
    for b in blocks:
        try:
            tree = ast.parse(b)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        names.add(tgt.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    names.add(alias.asname or alias.name.split(".")[0])
    return names


def check_critical(critical: list[str], defined: set[str]) -> list[str]:
    return [n for n in critical if n not in defined]


def find_attr_refs(blocks: list[str], aliases: tuple[str, ...]) -> set[str]:
    """在拼接文本上扫 alias.X 的属性访问 X 集合。"""
    pattern = r"(?:" + "|".join(re.escape(a) for a in aliases) + r")\.([a-zA-Z_]\w*)"
    refs: set[str] = set()
    for b in blocks:
        refs.update(re.findall(pattern, b))
    return refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="plan §11 自检 -- 抽提 + 签名一致性检查")
    parser.add_argument("plan", type=Path, help="plan markdown 路径")
    parser.add_argument(
        "--critical",
        nargs="+",
        default=[],
        help="关键符号清单 -- 必须在 plan 中有 def/class/assign/import",
    )
    parser.add_argument(
        "--alias",
        nargs="+",
        default=("lib", "app", "g", "mod"),
        help="跨段属性引用前缀(默认 lib app g mod)",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if not args.plan.exists():
        print(f"[error] plan 不存在: {args.plan}", file=sys.stderr)
        return 2

    blocks = extract_python_blocks(args.plan)
    print(f"[info] 抽到 {len(blocks)} 段 Python 块")

    syntax_errors = check_syntax(blocks)
    if syntax_errors:
        print(f"[FAIL] 语法错误 {len(syntax_errors)} 处:")
        for e in syntax_errors:
            print(f"  - {e}")
        return 1
    print(f"[ok] {len(blocks)} 段 Python 块语法全部合法")

    defined = collect_defined_names(blocks)
    if args.verbose:
        plan_defined = sorted(defined - DEFAULT_BUILTINS)
        print(f"[info] plan 中定义的符号 ({len(plan_defined)}): {plan_defined}")

    if args.critical:
        missing = check_critical(args.critical, defined)
        if missing:
            print(f"[FAIL] 关键符号未定义: {missing}")
            return 1
        print(f"[ok] {len(args.critical)} 个关键符号全部在 plan 中定义")

    refs = find_attr_refs(blocks, tuple(args.alias))
    unknown_refs = sorted(r for r in refs if r not in defined)
    if unknown_refs:
        # 不视为 fail -- 标准库属性等大量误报正常,只警告
        if args.verbose:
            print(f"[warn] {len(unknown_refs)} 个跨段属性访问 plan 未定义(可能是标准库): {unknown_refs}")
        else:
            print(f"[warn] {len(unknown_refs)} 个跨段属性访问 plan 未定义(--verbose 看清单)")
    else:
        print("[ok] 所有跨段属性访问都对应到 plan 定义")

    print("[done] plan §11 自检通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
