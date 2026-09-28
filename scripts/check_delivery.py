"""检查功能交付登记的完整性、审核状态与指纹；不会自动刷新指纹或替代语义复核。"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

FIXED_KINDS = {'config', 'bi', 'art', 'audio'}


def check_delivery(manifest: Path) -> list[str]:
    errors = []
    try:
        data = json.loads(manifest.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or data.get('schema_version') != 1:
            return ['不支持的登记格式']
        if data.get('mode') not in {'small', 'complete'} or not data.get('feature'):
            errors.append('缺少功能名或有效交付模式')
        if data.get('known_issues'):
            errors.extend(f'已登记待处理：{issue}' for issue in data['known_issues'])
        source = data['source']
        artifacts = data['artifacts']
        if not isinstance(source, dict) or not isinstance(artifacts, list):
            return ['source 必须是对象，artifacts 必须是数组']
        seen = set()
        kinds = set()
        for entry in [source, *artifacts]:
            if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
                errors.append('产物缺少有效路径')
                continue
            path = (manifest.parent / entry['path']).resolve()
            if entry is not source:
                if path in seen:
                    errors.append(f'重复登记：{entry["path"]}')
                seen.add(path)
                kinds.add(entry.get('kind'))
                if entry.get('status') != 'reviewed' or not entry.get('review_note', '').strip():
                    errors.append(f'尚未核验：{entry["path"]}')
            if not path.is_file():
                errors.append(f'文件缺失：{entry["path"]}')
            elif hashlib.sha256(path.read_bytes()).hexdigest() != entry.get('sha256'):
                errors.append(f'内容已变化，重新核验后才能刷新指纹：{entry["path"]}')
        if data.get('mode') == 'complete':
            missing = FIXED_KINDS - kinds
            if missing:
                errors.append('缺少固定派生：' + ', '.join(sorted(missing)))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append(f'无法核验登记：{exc}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifests', nargs='+', type=Path)
    args = parser.parse_args()
    failures = 0
    for p in args.manifests:
        issues = check_delivery(p)
        failures += len(issues)
        print(f'{p}: ' + ('待处理' if issues else '登记与已记录核验基线一致'))
        for issue in issues:
            print('  ' + issue)
    print('指纹一致不证明业务正确，语义核验由 review_note 对应的审核负责。')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
