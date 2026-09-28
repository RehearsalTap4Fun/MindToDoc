"""只读检查指定 Markdown 文件；退出 0 表示机械检查通过，不代表语义审核通过。

--baseline <git-ref>：只报告相对该版本新增的问题（按问题类型与行内容比对），
用于局部修订；新稿与完整重整不加此参数，须零问题。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class ResourceLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in {'src', 'href'} and value)


def check_document(path: Path, text: str | None = None) -> list[dict]:
    issues = []

    def add(line, code, message):
        content = lines[line - 1].strip() if 0 < line <= len(lines) else ''
        issues.append({'file': str(path), 'line': line, 'code': code, 'message': message, 'text': content})

    lines = []
    if text is None:
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
        # 行内代码是字段名、示例值或原样文案，不参与占位、链接和分号检查。
        plain = re.sub(r'(`+)(?!`).*?(?<!`)\1(?!`)', '', s)
        if re.search(r'\{\{(?!red:)[^}]+\}\}|\b(?:TODO|TBD)\b', plain):
            add(n, 'placeholder', '仍有模板占位或 TODO/TBD')
        html = ResourceLinks()
        html.feed(plain)
        links = re.findall(r'!?\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', plain)
        definition = re.match(r'^\[[^\]]+\]:\s*(<[^>]+>|\S+)', plain)
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
        if '；' in plain:
            add(n, 'semicolon', '按语义拆分分号两侧规则，保留条件和因果关系')
        if not re.match(r'^(?:[-*+]\s|\d+[.)]\s)', s) and len(s) >= 75:
            add(n, 'long-prose', '散文段落达到 75 字，请按语义分组')
    if fence:
        add(len(lines), 'unclosed-fence', '代码块未闭合')
    return issues


def baseline_text(path: Path, ref: str) -> str | None:
    """读取 path 在 git ref 中的内容；该版本不存在此文件时返回 None。"""
    folder = path.resolve().parent
    proc = subprocess.run(['git', '-C', str(folder), 'show', f'{ref}:./{path.name}'],
                          capture_output=True)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode('utf-8-sig', errors='replace')


def new_issues(path: Path, ref: str) -> list[dict]:
    current = check_document(path)
    old_text = baseline_text(path, ref)
    if old_text is None:
        return current
    # 同类问题按行内容计数抵扣；行号变化不算新增，行内容改动后仍有问题则算新增。
    remaining = Counter((i['code'], i['text']) for i in check_document(path, old_text))
    fresh = []
    for issue in current:
        key = (issue['code'], issue['text'])
        if remaining[key]:
            remaining[key] -= 1
        else:
            fresh.append(issue)
    return fresh


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--baseline', metavar='GIT_REF', help='只报告相对该 git 版本新增的问题')
    args = parser.parse_args()
    if args.baseline:
        issues = [i for p in args.files for i in new_issues(p, args.baseline)]
    else:
        issues = [i for p in args.files for i in check_document(p)]
    if args.json:
        print(json.dumps(issues, ensure_ascii=False, indent=2))
    else:
        for i in issues:
            print(f"{i['file']}:{i['line']} [{i['code']}] {i['message']}")
        scope = f'相对 {args.baseline} 新增 ' if args.baseline else ''
        print(f'机械检查：{len(args.files)} 文件，{scope}{len(issues)} 问题；仍需语义审核')
    return 1 if issues else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
