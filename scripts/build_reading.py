"""Render the books (and, once connected, podcasts) on reading.html from data/*.json.

Run from the repo root: python3 scripts/build_reading.py
Only the region between the reading:start and reading:end markers is rewritten.
"""
import html
import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'reading.html')
START, END = '<!-- reading:start -->', '<!-- reading:end -->'


def esc(s):
    return html.escape(s, quote=False)


def books_html():
    data = json.load(open(os.path.join(ROOT, 'data', 'books.json'), encoding='utf-8'))
    shown = [b for b in data['books'] if not b.get('hidden')]
    current = [b for b in shown if b.get('status') == 'reading']
    done = [b for b in shown if b.get('status', 'read') == 'read']

    seen = set()
    for b in sorted(done, key=lambda b: b['finished']):
        key = (b['title'].lower(), b['author'].lower())
        b['_again'] = key in seen
        seen.add(key)

    undated = [b for b in done if not b['finished']]
    years = OrderedDict()
    for b in sorted((b for b in done if b['finished']), key=lambda b: b['finished'], reverse=True):
        years.setdefault(b['finished'][:4], []).append(b)

    out = []
    out.append(f'        <p class="reading-stats">{len(done)} books so far, updated daily from Goodreads and Spotify.</p>\n')
    if current:
        out.append('        <h2>Reading now</h2>\n        <ul class="shelf">\n')
        for b in current:
            out.append(f'          <li><span class="shelf__title">{esc(b["title"])}</span> <span class="shelf__by">{esc(b["author"])}</span></li>\n')
        out.append('        </ul>\n')
    for y, items in years.items():
        n = len(items)
        out.append(f'        <h2>{y} <span class="shelf__count">{n} book{"s" if n != 1 else ""}</span></h2>\n        <ul class="shelf">\n')
        for b in items:
            again = ' <span class="shelf__tag">read again</span>' if b['_again'] else ''
            out.append(f'          <li><span class="shelf__title">{esc(b["title"])}</span> <span class="shelf__by">{esc(b["author"])}</span>{again}<span class="shelf__genre">{esc(b["genre"])}</span></li>\n')
        out.append('        </ul>\n')
    if undated:
        out.append('        <h2>Also read</h2>\n        <ul class="shelf">\n')
        for b in sorted(undated, key=lambda b: b['title']):
            out.append(f'          <li><span class="shelf__title">{esc(b["title"])}</span> <span class="shelf__by">{esc(b["author"])}</span><span class="shelf__genre">{esc(b["genre"])}</span></li>\n')
        out.append('        </ul>\n')
    return ''.join(out)


def podcasts_html():
    path = os.path.join(ROOT, 'data', 'podcasts.json')
    if not os.path.exists(path):
        return ''
    shows = [s for s in json.load(open(path, encoding='utf-8'))['shows'] if not s.get('hidden')]
    if not shows:
        return ''
    out = ['        <h2 id="podcasts">Podcasts I follow</h2>\n        <ul class="shelf">\n']
    for s in shows:
        out.append(f'          <li><a class="shelf__title" href="{html.escape(s["url"])}">{esc(s["name"])}</a> <span class="shelf__by">{esc(s.get("publisher", ""))}</span></li>\n')
    out.append('        </ul>\n')
    return ''.join(out)


def main():
    page = open(PAGE, encoding='utf-8').read()
    i, j = page.index(START) + len(START), page.index(END)
    body = '\n' + books_html() + podcasts_html() + '        '
    new = page[:i] + body + page[j:]
    if new != page:
        open(PAGE, 'w', encoding='utf-8').write(new)
        print('reading.html updated')
    else:
        print('reading.html unchanged')


if __name__ == '__main__':
    main()
