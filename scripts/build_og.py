"""Share images (the picture a link shows on LinkedIn, Slack or in a text), rendered with headless Chrome
from og/card.html.

Run from the repo root: python3 scripts/build_og.py

- Home card (assets/img/og.png): redrawn when the ERCOT year behind its heatmap changes (each January).
- One card per weekly post (assets/img/og/<slug>.png): drawn once, when the post first appears.
If Chrome is missing or fails, a post gets a copy of the home card, so its link preview never breaks.
"""
import functools
import glob
import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.join(ROOT, 'assets', 'img', 'og.png')
POSTS = os.path.join(ROOT, 'assets', 'img', 'og')
STATE = os.path.join(ROOT, 'data', 'og.json')
CANDIDATES = [os.environ.get('CHROME', ''), 'google-chrome', 'chromium',
              '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']


def chrome():
    for c in CANDIDATES:
        if c and (shutil.which(c) or os.path.exists(c)):
            return shutil.which(c) or c
    return None


def render(query, out, server):
    exe = chrome()
    if not exe:
        raise RuntimeError('no Chrome')
    tmp = os.path.join(tempfile.mkdtemp(), 'card.png')
    url = f'http://127.0.0.1:{server.server_address[1]}/og/card.html?{urllib.parse.urlencode(query)}'
    subprocess.run([exe, '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
                    '--force-prefers-reduced-motion', '--virtual-time-budget=8000', '--window-size=1200,630',
                    f'--screenshot={tmp}', url], check=True, capture_output=True, timeout=120)
    if os.path.getsize(tmp) < 10000:
        raise RuntimeError('blank render')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.copyfile(tmp, out)


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    facts = json.load(open(os.path.join(ROOT, 'data', 'facts.json'), encoding='utf-8'))
    year = facts.get('ercot.year')
    posts = [json.load(open(p, encoding='utf-8')) for p in sorted(glob.glob(os.path.join(ROOT, 'posts', '*.json')))]
    posts = [p for p in posts if not p.get('draft')]
    todo_home = state.get('home_year') != year or not os.path.exists(HOME)
    todo_posts = [p for p in posts if not os.path.exists(os.path.join(POSTS, p['slug'] + '.png'))]
    if not todo_home and not todo_posts:
        print('share images up to date')
        return

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        if todo_home:
            try:
                render({'kind': 'home', 'above': facts.get('ercot.hours_above', '')}, HOME, srv)
                state['home_year'] = year
                print(f'home share image redrawn for {year}')
            except Exception as e:  # noqa: BLE001 - keep the old card
                print(f'::warning::home share image not redrawn: {e}')
        for p in todo_posts:
            out = os.path.join(POSTS, p['slug'] + '.png')
            try:
                render({'title': p['title'], 'dek': p['dek'], 'label': p.get('series') or 'Writing'}, out, srv)
                print('share image for', p['slug'])
            except Exception as e:  # noqa: BLE001
                shutil.copyfile(HOME, out)
                print(f'::warning::{p["slug"]}: used the home card ({e})')
    finally:
        srv.shutdown()
    open(STATE, 'w').write(json.dumps(state, indent=1) + '\n')


if __name__ == '__main__':
    main()
