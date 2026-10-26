"""Fill every <span data-fact="key">…</span> on the site from data/facts.json,
and stamp site.css / site.js links with a content hash so browsers never use a stale copy.

Run from anywhere: python3 scripts/build_facts.py
Only the text inside marked spans changes. Unknown keys are reported and left alone.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import datetime
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPAN = re.compile(r'(<span data-fact="([^"]+)">)(.*?)(</span>)', re.S)


ASSET = re.compile(r'(assets/(?:css/site\.css|js/site\.js))(\?v=[0-9a-f]+)?')


def asset_versions():
    out = {}
    for rel in ('assets/css/site.css', 'assets/js/site.js'):
        out[rel] = hashlib.sha256(open(os.path.join(ROOT, rel), 'rb').read()).hexdigest()[:10]
    return out


def derived_facts():
    """Facts computed from the site itself, never typed: the footer's "Updated" month comes from the
    latest commit, and the glossary count from the glossary page."""
    out = {}
    try:
        d = subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%cs'], capture_output=True, text=True, timeout=30).stdout.strip()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d):
            out['site.updated'] = datetime.date.fromisoformat(d).strftime('%B %Y')
    except (OSError, subprocess.SubprocessError):
        pass
    gloss = os.path.join(ROOT, 'bitcoin-glossary.html')
    if os.path.exists(gloss):
        n = len(re.findall(r'<dt>', open(gloss, encoding='utf-8').read()))
        if n:
            out['glossary.terms'] = str(n)
    return out


def main():
    versions = asset_versions()
    facts = json.load(open(os.path.join(ROOT, 'data', 'facts.json'), encoding='utf-8'))
    facts.update(derived_facts())
    changed, unknown = [], set()
    for path in sorted(glob.glob(os.path.join(ROOT, '*.html')) + glob.glob(os.path.join(ROOT, 'notes', '*.html'))):
        s = open(path, encoding='utf-8').read()

        def fill(m):
            key = m.group(2)
            if key not in facts:
                unknown.add(key)
                return m.group(0)
            return m.group(1) + facts[key] + m.group(4)

        new = SPAN.sub(fill, s)
        new = ASSET.sub(lambda m: f'{m.group(1)}?v={versions[m.group(1)]}', new)
        if new != s:
            open(path, 'w', encoding='utf-8').write(new)
            changed.append(os.path.basename(path))
    print('facts applied:', ', '.join(changed) if changed else 'no changes')
    if unknown:
        print('unknown fact keys:', ', '.join(sorted(unknown)), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
