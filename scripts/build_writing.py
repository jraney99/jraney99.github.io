"""Build writing.html (everything Jack has written) and a page for each weekly post.

Run from the repo root: python3 scripts/build_writing.py

Hand-made pages are listed in data/writing.json. Weekly posts live in posts/*.json and
are rendered to notes/<slug>.html, then added to the list automatically. A post file
looks like this (body is plain text: blank lines between paragraphs, "## " for a
heading, "- " for a list item, **bold** and [text](url) inline):

    {"slug": "archibald-week-1", "title": "...", "dek": "...", "date": "2026-10-27",
     "topic": "ai", "series": "Building Archibald", "body": "...",
     "github": "https://github.com/jraney99/archibald-agent/compare/..."}

Posts with "draft": true are skipped. The build fails on an em dash anywhere in a post.
Only the region between the writing:start and writing:end markers of writing.html is rewritten.
"""
import glob
import html
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'writing.html')
TEMPLATE = os.path.join(ROOT, 'building-an-agent.html')
START, END = '<!-- writing:start -->', '<!-- writing:end -->'
REQUIRED = ('slug', 'title', 'dek', 'date', 'topic', 'body')


def esc(s):
    return html.escape(s, quote=False)


def month(d):
    return date.fromisoformat(d).strftime('%B %Y')


def day(d):
    x = date.fromisoformat(d)
    return f'{x.strftime("%B")} {x.day}, {x.year}'


def inline(s):
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)

    def link(m):
        url = html.unescape(m.group(2))
        if not re.match(r'^(https://|[a-z0-9-]+\.html(#[\w-]+)?$)', url):
            sys.exit(f'Link not allowed in a post: {url}')
        if not url.startswith('https://'):
            url = '../' + url
        return f'<a class="inline-link" href="{html.escape(url)}">{m.group(1)}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, s)


def body_html(text):
    out = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = [l.strip() for l in block.strip().split('\n')]
        if lines[0].startswith('## '):
            out.append(f'        <h2>{inline(lines[0][3:])}</h2>')
            lines = lines[1:]
            if not lines:
                continue
        if all(l.startswith('- ') for l in lines):
            items = ''.join(f'\n          <li>{inline(l[2:])}</li>' for l in lines)
            out.append(f'        <ul>{items}\n        </ul>')
        else:
            out.append(f'        <p>{inline(" ".join(lines))}</p>')
    return '\n'.join(out)


def load_posts():
    posts = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'posts', '*.json'))):
        p = json.load(open(path, encoding='utf-8'))
        missing = [k for k in REQUIRED if not p.get(k)]
        if missing:
            sys.exit(f'{os.path.basename(path)} is missing: {", ".join(missing)}')
        if '—' in json.dumps(p, ensure_ascii=False):
            sys.exit(f'{os.path.basename(path)} contains an em dash')
        if not re.fullmatch(r'[a-z0-9-]+', p['slug']):
            sys.exit(f'{os.path.basename(path)}: slug must be lowercase letters, numbers and hyphens')
        date.fromisoformat(p['date'])
        if not p.get('draft'):
            posts.append(p)
    return sorted(posts, key=lambda p: p['date'], reverse=True)


def relative(page):
    """Point the template's local links one folder up, for pages in notes/."""
    return re.sub(r'((?:href|src)=")(?!https?:|#|mailto:|/|data:)', r'\1../', page)


def render_post(p, topics, older):
    src = open(TEMPLATE, encoding='utf-8').read()
    head = src[:src.index('<main id="main">')]
    foot = src[src.index('</main>'):]
    url = f'https://jackraney.com/notes/{p["slug"]}'
    t, d = html.escape(p['title']), html.escape(p['dek'])
    head = re.sub(r'<title>[^<]*</title>', f'<title>{t} · Jack Raney</title>', head)
    head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{d}">', head)
    head = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', head)
    head = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">', head)
    head = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{t}">', head)
    head = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{d}">', head)
    head = re.sub(r'article:published_time" content="[^"]*"', f'article:published_time" content="{p["date"]}"', head)
    head = re.sub(r'<meta property="og:image" content="[^"]*">',
                  f'<meta property="og:image" content="https://jackraney.com/assets/img/og/{p["slug"]}.png">', head)
    label = esc(p.get('series') or topics.get(p['topic'], ''))
    gh = ''
    if p.get('github'):
        if not p['github'].startswith('https://github.com/jraney99/'):
            sys.exit(f'{p["slug"]}: github link must point to github.com/jraney99')
        gh = f'\n        <p class="memo__source">The code behind this week’s changes is public: <a class="inline-link" href="{html.escape(p["github"])}">see it on GitHub</a>.</p>'
    if older:
        nxt = f'notes/{older["slug"]}.html', esc(older['title'])
    else:
        nxt = 'writing.html', 'All writing'
    main = f'''<main id="main">
  <article>
    <header class="wrap doc-head">
      <div class="doc-head__inner">
        <a class="back" href="writing.html">← All writing</a>
        <h1>{esc(p["title"])}</h1>
        <p class="dek">{esc(p["dek"])}</p>
        <p class="doc-date">{label} · <time datetime="{p["date"]}">{day(p["date"])}</time></p>
      </div>
    </header>

    <div class="wrap memo">
      <div class="prose">
{body_html(p["body"])}{gh}
      </div>

      <a class="next-link" href="{nxt[0]}">
        <span class="next-link__label">{"Previous" if older else "More"}</span>
        <span class="title">{nxt[1]} →</span>
      </a>

      <p class="ask">Questions or a different take? Email me at <a class="inline-link" href="mailto:jack@jackraney.com">jack@jackraney.com</a>.</p>
    </div>
  </article>
'''
    return relative(head + main + foot)


def list_html(items, topics):
    used = [k for k in topics if any(i['topic'] == k for i in items)]
    out = ['        <div class="wfilter" role="group" aria-label="Filter by topic">\n',
           '          <button type="button" aria-pressed="true" data-topic="all">All</button>\n']
    for k in used:
        out.append(f'          <button type="button" aria-pressed="false" data-topic="{k}">{esc(topics[k])}</button>\n')
    out.append('        </div>\n')
    out.append(f'        <p class="wcount" id="wcount" aria-live="polite">{len(items)} pieces</p>\n')
    out.append('        <ul class="wlist">\n')
    for i in items:
        meta = ' · '.join(x for x in (i.get('series') or i.get('kind', ''), topics.get(i['topic'], ''), month(i['date'])) if x)
        out.append(f'          <li data-topic="{i["topic"]}"><a href="{html.escape(i["url"])}">'
                   f'<span class="wlist__meta">{esc(meta)}</span>'
                   f'<span class="wlist__title">{esc(i["title"])}</span>'
                   f'<span class="wlist__dek">{esc(i["dek"])}</span></a></li>\n')
    out.append('        </ul>\n')
    return ''.join(out)


SITE = 'https://jackraney.com'


def canonical(path):
    path = path[:-5] if path.endswith('.html') else path
    return SITE + '/' if path == 'index' else f'{SITE}/{path}'


def write_if_changed(path, text):
    if not os.path.exists(path) or open(path, encoding='utf-8').read() != text:
        open(path, 'w', encoding='utf-8').write(text)
        print('wrote', os.path.relpath(path, ROOT))


def sitemap():
    pages = sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, '*.html')) + glob.glob(os.path.join(ROOT, 'notes', '*.html'))
                   if os.path.basename(p) != '404.html'
                   and not os.path.basename(p).startswith('golf-'))  # golf deep pages stay unlisted by Jack's choice
    pages.sort(key=lambda p: p != 'index.html')
    urls = ''.join(f'  <url><loc>{canonical(p)}</loc></url>\n' for p in pages)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n'


def feed(items):
    """RSS 2.0 for the Writing page, newest 30 pieces."""
    def rfc822(d):
        return date.fromisoformat(d).strftime('%a, %d %b %Y 12:00:00 +0000')
    entries = ''
    for i in items[:30]:
        link = canonical(i['url'])
        entries += (f'  <item><title>{html.escape(i["title"])}</title><link>{link}</link><guid>{link}</guid>'
                    f'<pubDate>{rfc822(i["date"])}</pubDate><description>{html.escape(i["dek"])}</description></item>\n')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>\n'
            f'  <title>Jack Raney: writing</title><link>{SITE}/writing</link>\n'
            '  <description>Case studies, memos, essays and tools by Jack Raney.</description>\n'
            f'{entries}</channel></rss>\n')


def main():
    data = json.load(open(os.path.join(ROOT, 'data', 'writing.json'), encoding='utf-8'))
    topics = data['topics']
    posts = load_posts()
    for p in posts:
        if p['topic'] not in topics:
            sys.exit(f'{p["slug"]}: unknown topic {p["topic"]}')

    os.makedirs(os.path.join(ROOT, 'notes'), exist_ok=True)
    keep = set()
    for n, p in enumerate(posts):
        same = [q for q in posts[n + 1:] if q.get('series') == p.get('series')]
        path = os.path.join(ROOT, 'notes', p['slug'] + '.html')
        keep.add(path)
        new = render_post(p, topics, same[0] if same else None)
        if not os.path.exists(path) or open(path, encoding='utf-8').read() != new:
            open(path, 'w', encoding='utf-8').write(new)
            print('wrote', os.path.relpath(path, ROOT))
    for path in glob.glob(os.path.join(ROOT, 'notes', '*.html')):
        if path not in keep:
            os.remove(path)
            print('removed', os.path.relpath(path, ROOT))

    items = [dict(url=f'notes/{p["slug"]}.html', kind='Note', **{k: p[k] for k in ('topic', 'date', 'title', 'dek')},
                  series=p.get('series')) for p in posts]
    order = {id(i): n for n, i in enumerate(items + data['items'])}
    items = sorted(items + data['items'], key=lambda i: (i['date'], -order[id(i)]), reverse=True)

    write_if_changed(os.path.join(ROOT, 'sitemap.xml'), sitemap())
    write_if_changed(os.path.join(ROOT, 'feed.xml'), feed(items))

    page = open(PAGE, encoding='utf-8').read()
    a, b = page.index(START) + len(START), page.index(END)
    new = page[:a] + '\n' + list_html(items, topics) + '        ' + page[b:]
    if new != page:
        open(PAGE, 'w', encoding='utf-8').write(new)
        print('writing.html updated')
    else:
        print('writing.html unchanged')


if __name__ == '__main__':
    main()
