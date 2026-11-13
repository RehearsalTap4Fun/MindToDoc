"""列出一个图层目录里的界面图层：名称、来源 prefab、可改写的文字槽、可点击热区。

用法：python scripts/list_ui_layers.py <图层目录> [--write <清单.md>]
不带 --write 时打印到屏幕；带上时把清单写成 Markdown（含缩略图链接），用于常用界面库的 README。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def rows(layer_dir: Path) -> list[dict]:
    out = []
    for meta_path in sorted(layer_dir.glob('*.json')):
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if 'image' in meta and 'name' in meta:
            out.append(meta)
    return out


def table(layers: list[dict], image_base: str) -> str:
    lines = ['| 图层 | 界面 | 预览 | 文字槽 | 热区 | 说明 |', '|---|---|---|---|---|---|']
    for m in layers:
        slots = '、'.join(f'`{k}`' for k in m.get('slots') or {}) or '无'
        hots = '、'.join(f'`{k}`' for k in m.get('hotspots') or {}) or '无'
        prefab = Path(m.get('prefab', '')).stem
        lines.append(f"| `{m['name']}` | {m.get('title') or prefab} | <img src=\"{image_base}{m['image']}\" width=\"120\"> | {slots} | {hots} | "
                     f"{m.get('note', '')} 来源：`{prefab}` |")
    return '\n'.join(lines)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('layer_dir', type=Path)
    parser.add_argument('--write', type=Path)
    args = parser.parse_args()
    layers = rows(args.layer_dir)
    if not layers:
        print(f'问题：目录里没有图层：{args.layer_dir}')
        return 1
    if not args.write:
        print(table(layers, str(args.layer_dir) + '/'))
        return 0
    base = os.path.relpath(args.layer_dir, args.write.parent).replace(os.sep, '/') + '/'
    marker = '<!-- 图层清单：由 scripts/list_ui_layers.py 生成，不手改 -->'
    body = marker + '\n' + table(layers, base) + '\n'
    old = args.write.read_text(encoding='utf-8') if args.write.exists() else ''
    text = old[:old.index(marker)] + body if marker in old else (old.rstrip() + '\n\n' if old else '') + body
    args.write.write_text(text, encoding='utf-8')
    print(f'已写入 {len(layers)} 个图层的清单：{args.write}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
