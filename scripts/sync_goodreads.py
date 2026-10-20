"""Add newly finished Goodreads books to data/books.json.

Reads the public RSS feeds for the "read" and "currently-reading" shelves.
Needs GOODREADS_USER_ID (the number in goodreads.com/user/show/<id>-name).
Existing entries, including hidden ones, are never changed or duplicated.
A finished book with no "date read" on Goodreads is kept undated rather than guessed.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'books.json')
FEED = 'https://www.goodreads.com/review/list_rss/{uid}?shelf={shelf}&per_page=200'


def fetch(uid, shelf):
    req = urllib.request.Request(FEED.format(uid=uid, shelf=shelf), headers={'User-Agent': 'jackraney.com reading sync'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return [(i.findtext('title') or '').strip() and i for i in ET.fromstring(r.read()).iter('item')]


def norm(title):
    t = title.lower().replace('&', ' and ').split(':')[0].split('(')[0]
    return re.sub(r'[^a-z0-9]+', '', t)


def short(title):
    return title.split(':')[0].split(' (')[0].strip()


def read_date(item):
    try:
        return parsedate_to_datetime(item.findtext('user_read_at')).date().isoformat()
    except (TypeError, ValueError):
        return ''


def main():
    uid = os.environ.get('GOODREADS_USER_ID', '').strip()
    if not uid:
        print('GOODREADS_USER_ID not set; skipping Goodreads')
        return
    try:
        read_items = [i for i in fetch(uid, 'read') if i is not None and i != '']
        now_items = [i for i in fetch(uid, 'currently-reading') if i is not None and i != '']
    except Exception as e:
        print(f'Goodreads feed failed, nothing changed: {e}', file=sys.stderr)
        return

    data = json.load(open(DATA, encoding='utf-8'))
    books = data['books']
    hidden = set(json.load(open(os.path.join(ROOT, 'data', 'hidden.json'))).get('sha256', []))
    skip = lambda title: hashlib.sha256(norm(title).encode()).hexdigest() in hidden
    added = 0

    # Finished books: promote a reading-now entry, or add if not already listed.
    for item in read_items:
        if skip(item.findtext('title')):
            continue
        key = norm(item.findtext('title'))
        reading = next((b for b in books if b.get('status') == 'reading' and norm(b['title']) == key), None)
        if reading:
            reading['status'], reading['finished'] = 'read', read_date(item)
            continue
        if any(norm(b['title']) == key for b in books):
            continue
        books.append({'title': short(item.findtext('title')), 'author': (item.findtext('author_name') or '').strip(),
                      'genre': '', 'finished': read_date(item), 'hidden': False, 'source': 'goodreads'})
        added += 1

    # Reading now mirrors the shelf exactly.
    on_shelf = {norm(i.findtext('title')): i for i in now_items if not skip(i.findtext('title'))}
    books[:] = [b for b in books if b.get('status') != 'reading' or norm(b['title']) in on_shelf]
    for key, item in on_shelf.items():
        if not any(norm(b['title']) == key for b in books):
            books.append({'title': short(item.findtext('title')), 'author': (item.findtext('author_name') or '').strip(),
                          'genre': '', 'finished': '', 'status': 'reading', 'hidden': False, 'source': 'goodreads'})

    json.dump(data, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'Goodreads: {added} finished books added, {len(on_shelf)} reading now')


if __name__ == '__main__':
    main()
