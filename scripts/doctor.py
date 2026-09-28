"""只读检查指定能力的本地依赖，不联网、不读取凭据、不自动安装。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path


def check_capability(root: Path, capability: dict, skill_roots: list[Path]) -> list[str]:
    errors = []
    for filename in capability.get('files', []):
        if not (root / filename).is_file():
            errors.append(f'缺少文件：{filename}')
    for module in capability.get('modules', []):
        if importlib.util.find_spec(module) is None:
            errors.append(f'缺少 Python 模块：{module}')
    for skill in capability.get('skills', []):
        if not any((folder / skill / 'SKILL.md').is_file() for folder in skill_roots):
            errors.append(f'缺少外部 Skill：{skill}；通过 --skill-root 指定所在目录')
    for command in capability.get('commands', []):
        if shutil.which(command) is None:
            errors.append(f'PATH 中缺少命令：{command}')
    return errors


def main():
    root = Path(__file__).resolve().parents[1]
    definitions = json.loads((root / 'dependencies.json').read_text(encoding='utf-8'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capability', action='append', choices=sorted(definitions), help='可重复；默认仅 core')
    parser.add_argument('--skill-root', action='append', type=Path, default=[])
    args = parser.parse_args()
    roots = [root / 'vendor/skills', *args.skill_root]
    failed = sys.version_info < (3, 9)
    if failed:
        print('需要 Python 3.9 或以上')
    for name in args.capability or ['core']:
        errors = check_capability(root, definitions[name], roots)
        print(f'{name}: ' + ('缺少依赖' if errors else '本地依赖齐备'))
        for error in errors:
            print('  ' + error)
        failed |= bool(errors)
    print('本检查不验证登录状态、远端服务、MCP 权限或产物质量。')
    return int(failed)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
