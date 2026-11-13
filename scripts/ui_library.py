"""常用界面库的获取流程：图层是项目美术资源，只放在本机，不进仓库；每台设备首次使用前要自己导出一次。

  python scripts/ui_library.py status  ui-library/k1              查看本机是否已获取、是否过期
  python scripts/ui_library.py prepare ui-library/k1              生成可直接交给 Unity 执行的导出代码
  python scripts/ui_library.py finish  ui-library/k1 [--client <客户端仓库>]   导出后核对、记录来源并生成清单

status 退出码：0 已获取且与规格一致；1 未获取、缺图层或规格已变，需要重新导出。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = ROOT / 'scripts/unity/export_ui_layers.cs'
STAMP = '.export.json'
sys.path.insert(0, str(ROOT / 'scripts'))
import list_ui_layers  # noqa: E402


def load_spec(lib: Path) -> tuple[dict, Path, str]:
    spec_path = lib / 'spec.json'
    if not spec_path.is_file():
        raise ValueError(f'不是常用界面库目录（缺少 spec.json）：{lib}')
    raw = spec_path.read_bytes()
    spec = json.loads(raw.decode('utf-8'))
    out = Path(spec.get('out', 'layers'))
    return spec, out if out.is_absolute() else lib / out, hashlib.sha256(raw).hexdigest()


def inspect(lib: Path) -> tuple[list[str], dict | None]:
    """返回问题列表与本机导出记录；问题为空表示可直接使用。"""
    spec, layer_dir, digest = load_spec(lib)
    names = [layer['name'] for layer in spec.get('layers', [])]
    missing = [n for n in names if not (layer_dir / f'{n}.json').is_file() or not (layer_dir / f'{n}.png').is_file()]
    if len(missing) == len(names):
        return [f'本机还没有获取这个库的图层（共 {len(names)} 个）'], None
    problems = [f'缺少图层：{"、".join(missing)}'] if missing else []
    stamp_path = layer_dir / STAMP
    stamp = json.loads(stamp_path.read_text(encoding='utf-8')) if stamp_path.is_file() else None
    if stamp is None:
        problems.append('图层已导出但没有完成记录：执行 finish 核对')
    elif stamp.get('spec_sha256') != digest:
        problems.append('导出规格在上次导出后有改动：重新导出')
    return problems, stamp


def client_info(client: Path | None) -> dict:
    if client is None:
        return {}
    info = {'client': str(client)}
    for key, cmd in (('branch', ['rev-parse', '--abbrev-ref', 'HEAD']), ('commit', ['rev-parse', '--short', 'HEAD'])):
        proc = subprocess.run(['git', '-C', str(client), *cmd], capture_output=True, text=True)
        if proc.returncode == 0:
            info[key] = proc.stdout.strip()
    return info


def cmd_status(lib: Path) -> int:
    problems, stamp = inspect(lib)
    if stamp:
        source = ' '.join(str(stamp[k]) for k in ('branch', 'commit') if stamp.get(k)) or '未记录客户端版本'
        print(f'上次导出：{stamp.get("exported_at")}（{source}），{stamp.get("layers")} 个图层')
    for problem in problems:
        print(f'问题：{problem}')
    if problems:
        print(f'获取方法：python scripts/ui_library.py prepare {lib}，按提示在 Unity 里执行，再执行 finish。')
        print('没有客户端工程或 Unity 时无法获取：预演里的这些界面用灰盒，并在交付说明里写明。')
        return 1
    print('常用界面库已获取，可直接用于交互预演。客户端界面改版后请重新导出。')
    return 0


def cmd_prepare(lib: Path) -> int:
    spec, layer_dir, _ = load_spec(lib)
    code = EXPORT_SCRIPT.read_text(encoding='utf-8').replace('__SPEC_PATH__', (lib / 'spec.json').resolve().as_posix())
    target = ROOT / '.codex_tmp' / 'ui-export' / f'{lib.resolve().name}-export.cs'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code, encoding='utf-8')
    print(f'导出代码已生成：{target}')
    print(f'将导出 {len(spec.get("layers", []))} 个图层到：{layer_dir}')
    print('下一步：')
    print('  1. 确认 Unity 编辑器已打开客户端工程，且没有在运行游戏。')
    print('  2. 读取上面的文件，把全文作为方法体交给 UnityMCP 的 execute_code 执行。')
    print('  3. 返回内容里出现“找不到 prefab”或“找不到节点”时，说明客户端界面已改动：先修正 spec.json 再重新执行。')
    print(f'  4. python scripts/ui_library.py finish {lib} --client <客户端仓库路径>')
    return 0


def cmd_finish(lib: Path, client: Path | None) -> int:
    spec, layer_dir, digest = load_spec(lib)
    names = [layer['name'] for layer in spec.get('layers', [])]
    errors = []
    for layer in spec.get('layers', []):
        meta_path = layer_dir / f"{layer['name']}.json"
        if not meta_path.is_file() or not (layer_dir / f"{layer['name']}.png").is_file():
            errors.append(f"缺少图层：{layer['name']}")
            continue
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        for key in ('slots', 'hotspots'):
            lost = sorted(set(layer.get(key) or {}) - set(meta.get(key) or {}))
            if lost:
                errors.append(f"{layer['name']} 的{'文字槽' if key == 'slots' else '热区'}没有导出：{'、'.join(lost)}（节点路径在客户端里已变化）")
    if errors:
        for error in errors:
            print(f'问题：{error}')
        return 1
    stamp = {'spec_sha256': digest, 'exported_at': datetime.date.today().isoformat(), 'layers': len(names), **client_info(client)}
    (layer_dir / STAMP).write_text(json.dumps(stamp, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    index = layer_dir / 'README.md'
    index.write_text('# 图层清单\n\n' + list_ui_layers.table(list_ui_layers.rows(layer_dir), '') + '\n', encoding='utf-8')
    print(f'已核对 {len(names)} 个图层并记录来源；清单：{index}')
    print('仍须逐张看图确认状态正确，脚本只核对文件、文字槽和热区是否齐全。')
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('command', choices=['status', 'prepare', 'finish'])
    parser.add_argument('library', type=Path)
    parser.add_argument('--client', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'status':
            return cmd_status(args.library)
        if args.command == 'prepare':
            return cmd_prepare(args.library)
        return cmd_finish(args.library, args.client)
    except (OSError, ValueError) as exc:
        print(f'问题：{exc}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
