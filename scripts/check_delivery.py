"""检查功能交付登记的完整性、审核状态与指纹；不替代语义复核。

检查：python scripts/check_delivery.py deliveries/<功能>.json
登记：逐个文件记录，完成该文件的语义复核后再执行，不做批量刷新。
  主案：--record <主案.md> --source [--feature 名称 --mode small|complete]（登记不存在时新建）
  派生：--record <文件> --kind bi --status reviewed --note "核验范围与规则落点"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
        known = data.get('known_issues')
        if known:
            errors.extend(f'已登记待处理：{issue}' for issue in ([known] if isinstance(known, str) else known))
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
                note = entry.get('review_note')
                if entry.get('status') != 'reviewed' or not isinstance(note, str) or not note.strip():
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(manifest: Path, target: Path, *, source=False, kind=None, status=None, note=None,
           feature=None, mode=None) -> str:
    """把单个文件的当前指纹写入登记；只动指定条目。"""
    if not target.is_file():
        raise ValueError(f'文件不存在：{target}')
    rel = Path(os.path.relpath(target.resolve(), manifest.resolve().parent)).as_posix()
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding='utf-8-sig'))
    else:
        if not (source and feature and mode):
            raise ValueError('登记不存在：先用 --source --feature --mode 登记主案')
        data = {'schema_version': 1, 'feature': feature, 'mode': mode, 'source': {}, 'artifacts': []}
    if feature:
        data['feature'] = feature
    if mode:
        data['mode'] = mode
    if source:
        data['source'] = {'path': rel, 'sha256': sha256(target)}
    else:
        if status not in {'reviewed', 'pending'}:
            raise ValueError('派生须指定 --status reviewed 或 pending')
        if status == 'reviewed' and not (note or '').strip():
            raise ValueError('reviewed 须用 --note 写明核验范围与规则落点')
        entry = next((a for a in data['artifacts'] if a.get('path') == rel), None)
        if entry is None:
            if not kind:
                raise ValueError('新登记的派生须指定 --kind')
            entry = {'kind': kind, 'path': rel}
            data['artifacts'].append(entry)
        if kind:
            entry['kind'] = kind
        entry.update({'sha256': sha256(target), 'status': status, 'review_note': note or ''})
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return rel


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('manifests', nargs='+', type=Path)
    parser.add_argument('--record', type=Path, metavar='FILE', help='登记单个文件的当前指纹')
    parser.add_argument('--source', action='store_true', help='--record 的文件是主案')
    parser.add_argument('--kind', help='派生类型：config、bi、art、audio、ui、image 等')
    parser.add_argument('--status', choices=['reviewed', 'pending'])
    parser.add_argument('--note', help='review_note：核验范围与规则落点')
    parser.add_argument('--feature')
    parser.add_argument('--mode', choices=['small', 'complete'])
    args = parser.parse_args()
    if args.record:
        if len(args.manifests) != 1:
            parser.error('--record 只能配一个登记文件')
        try:
            rel = record(args.manifests[0], args.record, source=args.source, kind=args.kind,
                         status=args.status, note=args.note, feature=args.feature, mode=args.mode)
        except (OSError, ValueError, TypeError) as exc:
            print(f'登记失败：{exc}')
            return 2
        print(f'已登记：{rel}')
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
