"""Fill every <span data-fact="key">…</span> on the site from data/facts.json.

Run from anywhere: python3 scripts/build_facts.py
Only the text inside marked spans changes. Unknown keys are reported and left alone.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPAN = re.compile(r'(<span data-fact="([^"]+)">)(.*?)(</span>)', re.S)


def main():
    facts = json.load(open(os.path.join(ROOT, 'data', 'facts.json'), encoding='utf-8'))
    changed, unknown = [], set()
    for path in sorted(glob.glob(os.path.join(ROOT, '*.html'))):
        s = open(path, encoding='utf-8').read()

        def fill(m):
            key = m.group(2)
            if key not in facts:
                unknown.add(key)
                return m.group(0)
            return m.group(1) + facts[key] + m.group(4)

        new = SPAN.sub(fill, s)
        if new != s:
            open(path, 'w', encoding='utf-8').write(new)
            changed.append(os.path.basename(path))
    print('facts applied:', ', '.join(changed) if changed else 'no changes')
    if unknown:
        print('unknown fact keys:', ', '.join(sorted(unknown)), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
