"""Add newly finished Goodreads books to data/books.json.

Goodreads stopped serving its RSS feeds in October 2026, so this reads the public widgets for the
"read" and "currently-reading" shelves, which need no key.
Needs GOODREADS_USER_ID (the number in goodreads.com/user/show/<id>-name).
Existing entries, including hidden ones, are never changed or duplicated.
The widgets give no finish date, so a new book is dated the day it first appears here.
An answer that is not a widget, or an empty read shelf, changes nothing and is recorded as a failure.
"""
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_status import record  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'books.json')
GRID = ('https://www.goodreads.com/review/grid_widget/{uid}?cover_size=medium&num_books=200'
        '&order=d&shelf={shelf}&sort=date_read')
# Five books at a time and it ignores the shelf, so it only ever supplies authors.
AUTHORS = ('https://www.goodreads.com/review/custom_widget/{uid}.Read?cover_position=left&cover_size=small'
           '&num_books=20&order=d&shelf=read&show_author=1&show_cover=0&show_rating=0&show_review=0'
           '&show_tags=0&show_title=1&sort={sort}&widget_id=1')


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'jackraney.com reading sync'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')


def widget(text, marker):
    if 'widget_code' not in text or marker not in text:
        raise ValueError('Goodreads did not answer with its widget')
    return text.replace('\\"', '"').replace('\\/', '/').replace('\\n', '\n').replace("\\'", "'")


def parse_grid(text):
    """[(review id, title)] for one shelf."""
    rows = re.findall(r'<a title="([^"]+)"[^>]*href="[^"]*/review/show/(\d+)', widget(text, 'gr_grid_container'))
    return [(review, re.sub(r'\s+', ' ', html.unescape(title)).strip()) for title, review in rows]


def parse_authors(text):
    """{review id: author}."""
    authors = {}
    for row in widget(text, 'gr_custom_container').split('gr_custom_each_container')[1:]:
        review = re.search(r'/review/show/(\d+)', row)
        author = re.search(r'gr_custom_author[^>]*>\s*by\s*<a[^>]*>(.*?)</a>', row, re.S)
        if review and author:
            authors[review[1]] = html.unescape(author[1]).strip()
    return authors


def shelf(uid, name, authors):
    return [{'title': title, 'author': authors.get(review, '')}
            for review, title in parse_grid(fetch(GRID.format(uid=uid, shelf=name)))]


def norm(title):
    t = title.lower().replace('&', ' and ').split(':')[0].split('(')[0]
    return re.sub(r'[^a-z0-9]+', '', t)


def short(title):
    return title.split(':')[0].split(' (')[0].strip()


def main():
    uid = os.environ.get('GOODREADS_USER_ID', '').strip()
    if not uid:
        print('GOODREADS_USER_ID not set; skipping Goodreads')
        return
    try:
        authors = {}
        for sort in ('date_read', 'date_added'):
            authors.update(parse_authors(fetch(AUTHORS.format(uid=uid, sort=sort))))
        read_items = shelf(uid, 'read', authors)
        now_items = shelf(uid, 'currently-reading', authors)
        if not read_items:
            raise ValueError('the read shelf came back empty')
    except Exception as e:
        print(f'Goodreads feed failed, nothing changed: {e}', file=sys.stderr)
        record('goodreads', False, 'The Goodreads feed could not be read.')
        return
    record('goodreads', True)

    data = json.load(open(DATA, encoding='utf-8'))
    books = data['books']
    hidden = set(json.load(open(os.path.join(ROOT, 'data', 'hidden.json'))).get('sha256', []))
    skip = lambda title: hashlib.sha256(norm(title).encode()).hexdigest() in hidden
    added = 0

    # Finished books: promote a reading-now entry, or add if not already listed.
    today = date.today().isoformat()
    for item in read_items:
        if skip(item['title']):
            continue
        key = norm(item['title'])
        reading = next((b for b in books if b.get('status') == 'reading' and norm(b['title']) == key), None)
        if reading:
            reading['status'], reading['finished'] = 'read', today
            continue
        if any(norm(b['title']) == key for b in books):
            continue
        books.append({'title': short(item['title']), 'author': item['author'],
                      'genre': '', 'finished': today, 'hidden': False, 'source': 'goodreads'})
        added += 1

    # Reading now mirrors the shelf exactly.
    on_shelf = {norm(i['title']): i for i in now_items if not skip(i['title'])}
    books[:] = [b for b in books if b.get('status') != 'reading' or norm(b['title']) in on_shelf]
    for key, item in on_shelf.items():
        if not any(norm(b['title']) == key for b in books):
            books.append({'title': short(item['title']), 'author': item['author'],
                          'genre': '', 'finished': '', 'status': 'reading', 'hidden': False, 'source': 'goodreads'})

    json.dump(data, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'Goodreads: {added} finished books added, {len(on_shelf)} reading now')


if __name__ == '__main__':
    main()
