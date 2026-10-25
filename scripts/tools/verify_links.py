"""Check relative Markdown file targets (not heading fragments), offline."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote


def broken_links(root):
    root = Path(root)
    problems = []
    for path in sorted(root.rglob('*.md')):
        if '.git' in path.relative_to(root).parts:
            continue
        source = path.read_text(encoding='utf-8')
        source = re.sub(r'```.*?```', lambda m: '\n' * m.group().count('\n'), source, flags=re.S)
        for match in re.finditer(r'!?\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', source):
            target = match.group(1).strip('<>')
            if re.match(r'^(?:https?://|mailto:|#)', target):
                continue
            file_part = unquote(target.split('#', 1)[0])
            if file_part and not (path.parent / file_part).exists():
                problems.append({'file': path.relative_to(root).as_posix(), 'line': source[:match.start()].count('\n') + 1, 'target': target})
    return problems


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', nargs='?', type=Path, default=Path(__file__).resolve().parents[2])
    args = p.parse_args()
    problems = broken_links(args.root)
    print(json.dumps({'broken_relative_file_targets': len(problems), 'problems': problems}, ensure_ascii=False, indent=2))
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
