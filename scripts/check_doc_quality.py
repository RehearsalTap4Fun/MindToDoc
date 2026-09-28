"""只读检查指定 Markdown 文件；退出 0 表示机械检查通过，不代表语义审核通过。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class ResourceLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in {'src', 'href'} and value)


def check_document(path: Path) -> list[dict]:
    issues = []

    def add(line, code, message):
        issues.append({'file': str(path), 'line': line, 'code': code, 'message': message})

    try:
        text = path.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError) as exc:
        add(1, 'unreadable', str(exc))
        return issues
    # 保留行数，使多行注释后的报错位置与原文一致。
    text = re.sub(r'<!--.*?-->', lambda m: '\n' * m.group().count('\n'), text, flags=re.S)
    fence = None
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        s = line.strip()
        m = re.match(r'^(`{3,}|~{3,})', s)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            continue
        if fence or not s:
            continue
        if re.search(r'\{\{(?!red:)[^}]+\}\}|\b(?:TODO|TBD)\b', s):
            add(n, 'placeholder', '仍有模板占位或 TODO/TBD')
        html = ResourceLinks()
        html.feed(s)
        links = re.findall(r'!?\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', s)
        definition = re.match(r'^\[[^\]]+\]:\s*(<[^>]+>|\S+)', s)
        if definition:
            links.append(definition.group(1))
        for target in set(links + html.links):
            target = target.strip('<>')
            if target.startswith('#'):
                continue  # 章节语义与片段锚点由联合审核核对。
            parts = urlsplit(target)
            if parts.scheme in {'http', 'https', 'mailto', 'data'}:
                continue  # 不发远程请求。
            if parts.scheme and not re.match(r'^[A-Za-z]:[/\\]', target):
                add(n, 'unsupported-link', f'不支持的链接协议：{parts.scheme}')
                continue
            local = unquote(target.split('#', 1)[0].split('?', 1)[0])
            dest = Path(local)
            if not dest.is_absolute():
                dest = path.parent / dest
            if not dest.exists():
                add(n, 'missing-link', f'本地链接不存在：{target}')
        if s.startswith(('|', '#', '>', '<', '![')):
            continue
        if '；' in s:
            add(n, 'semicolon', '按语义拆分分号两侧规则，保留条件和因果关系')
        if not re.match(r'^(?:[-*+]\s|\d+[.)]\s)', s) and len(s) >= 75:
            add(n, 'long-prose', '散文段落达到 75 字，请按语义分组')
    if fence:
        add(len(lines), 'unclosed-fence', '代码块未闭合')
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    issues = [i for p in args.files for i in check_document(p)]
    if args.json:
        print(json.dumps(issues, ensure_ascii=False, indent=2))
    else:
        for i in issues:
            print(f"{i['file']}:{i['line']} [{i['code']}] {i['message']}")
        print(f'机械检查：{len(args.files)} 文件，{len(issues)} 问题；仍需语义审核')
    return 1 if issues else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
