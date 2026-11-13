"""把 Unity 导出的界面图层写入交互预演网页的 preview-ui 块（图片内嵌，保持单文件）。

用法：python scripts/build_preview_ui.py <来源>... <预演.html> [--design 1080 1920]
来源可以写多个，每个是一个导出目录（取其中全部图层）或单个图层的 <名称>.json（只取这一个）。
例：功能自己的图层目录，加上常用界面库里的通用确认弹窗
  python scripts/build_preview_ui.py output/ui-preview/<功能名>/layers ui-library/k1/layers/msgbox_two.json output/<功能名>-交互预演.html
图层由 scripts/unity/export_ui_layers.cs 生成：每个图层一份 <名称>.json 与 <名称>.png。
已有 preview-ui 块时整体替换；没有时插在引擎脚本之前。不修改其他内容。
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path

BLOCK = re.compile(r'<script type="application/json" id="preview-ui">.*?</script>\n?', re.S)
ANCHOR = '<!-- 引擎：不随功能修改 -->'
WARN_BYTES = 8 * 1024 * 1024


def build(sources: list[Path] | Path, design: list[int]) -> dict:
    layers = {}
    for source in ([sources] if isinstance(sources, Path) else sources):
        if not source.exists():
            hint = '；常用界面库的图层只放本机，先执行 python scripts/ui_library.py status <库目录> 按提示获取' if 'ui-library' in source.parts else ''
            raise ValueError(f'来源不存在：{source}{hint}')
        for meta_path in (sorted(source.glob('*.json')) if source.is_dir() else [source]):
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            if 'image' not in meta or 'name' not in meta:
                if not source.is_dir():
                    raise ValueError(f'不是图层文件：{meta_path}')
                continue  # 目录里的导出规格等其他 JSON
            image = meta_path.parent / meta['image']
            if not image.is_file():
                raise ValueError(f'缺少图层图片：{image}')
            if meta['name'] in layers:
                raise ValueError(f'图层重名：{meta["name"]}（{meta_path}）；同名图层只保留一个来源')
            layers[meta['name']] = {
                'prefab': meta.get('prefab', ''),
                'x': meta['x'], 'y': meta['y'], 'w': meta['w'], 'h': meta['h'],
                'hotspots': meta.get('hotspots') or {},
                'slots': meta.get('slots') or {},
                'src': 'data:image/png;base64,' + base64.b64encode(image.read_bytes()).decode('ascii'),
            }
    if not layers:
        raise ValueError('来源里没有图层')
    return {'design': design, 'layers': layers}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('paths', type=Path, nargs='+', metavar='来源... 预演.html')
    parser.add_argument('--design', type=int, nargs=2, default=[1080, 1920], metavar=('宽', '高'))
    args = parser.parse_args()
    if len(args.paths) < 2:
        parser.error('至少给出一个来源和预演网页')
    args.preview = args.paths[-1]
    try:
        ui = build(args.paths[:-1], args.design)
        html = args.preview.read_text(encoding='utf-8')
        block = ('<script type="application/json" id="preview-ui">\n'
                 + json.dumps(ui, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + '\n</script>\n')
        if BLOCK.search(html):
            html = BLOCK.sub(lambda _: block, html, count=1)
        elif ANCHOR in html:
            html = html.replace(ANCHOR, '<!-- 现有界面图层：由 scripts/build_preview_ui.py 生成，不手改 -->\n' + block + '\n' + ANCHOR, 1)
        else:
            raise ValueError('预演网页不是按模板生成的，找不到引擎脚本位置')
        args.preview.write_text(html, encoding='utf-8')
    except (OSError, ValueError, KeyError) as exc:
        print(f'问题：{exc}')
        return 1
    size = args.preview.stat().st_size
    print(f'已写入 {len(ui["layers"])} 个图层：{", ".join(ui["layers"])}；网页 {size / 1024 / 1024:.1f} MB')
    if size > WARN_BYTES:
        print('提示：网页超过 8 MB，可在导出规格里调低 scale 或裁掉不需要的整屏图层')
    return 0


if __name__ == '__main__':
    sys.exit(main())
