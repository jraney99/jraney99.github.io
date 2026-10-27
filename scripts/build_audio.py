#!/usr/bin/env python3
"""Add an audio player to any article Jack has recorded a reading of.

Drop a recording at assets/audio/<page>.m4a (or .mp3), named after the page file
(how-i-use-ai.m4a for how-i-use-ai.html, a post slug for notes/<slug>.html), and this
script puts a player at the top of that page. Delete the recording and the player goes.
Runs in CI right after build_writing.py, which regenerates note pages without the player.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / 'assets' / 'audio'
START, END = '<!-- audio -->', '<!-- /audio -->'


def block(src):
    return (f'{START}\n        <div class="audio-note"><p>Prefer to listen? This is me reading it.</p>\n'
            f'        <audio controls preload="metadata" src="/{src}"></audio></div>\n        {END}')


def page_for(stem):
    for p in (ROOT / 'notes' / f'{stem}.html', ROOT / f'{stem}.html'):
        if p.exists():
            return p
    return None


def pages_with_markers():
    pages = list(ROOT.glob('*.html'))
    if (ROOT / 'notes').is_dir():
        pages += list((ROOT / 'notes').glob('*.html'))
    return [p for p in pages if START in p.read_text()]


def main():
    AUDIO.mkdir(parents=True, exist_ok=True)
    recordings = {f.stem: f'assets/audio/{f.name}' for f in sorted(AUDIO.iterdir())
                  if f.suffix.lower() in ('.m4a', '.mp3')}
    problems = []
    for stem, src in recordings.items():
        page = page_for(stem)
        if page is None:
            problems.append(f'no page named {stem}.html for recording {src}')
            continue
        html = page.read_text()
        new = block(src)
        if START in html:
            out = re.sub(re.escape(START) + r'.*?' + re.escape(END), new, html, flags=re.S)
        elif '<div class="prose">' in html:
            out = html.replace('<div class="prose">', '<div class="prose">\n        ' + new, 1)
        else:
            problems.append(f'{page.name}: no <div class="prose"> to anchor the player')
            continue
        if out != html:
            page.write_text(out)
            print(f'player on {page.relative_to(ROOT)}')
    for page in pages_with_markers():
        html = page.read_text()
        m = re.search(re.escape(START) + r'.*?src="/(assets/audio/[^"]+)".*?' + re.escape(END), html, re.S)
        if m and m.group(1) in recordings.values():
            continue
        out = re.sub(r'\n?[ \t]*' + re.escape(START) + r'.*?' + re.escape(END) + r'\n?', '\n', html, flags=re.S)
        page.write_text(out)
        print(f'player removed from {page.relative_to(ROOT)}')
    if problems:
        sys.exit('; '.join(problems))


if __name__ == '__main__':
    main()
