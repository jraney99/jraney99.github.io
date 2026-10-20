"""Write the podcasts Jack follows on Spotify to data/podcasts.json.

Needs SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET and SPOTIFY_REFRESH_TOKEN
(create the token once with scripts/spotify_auth.py). Read-only access.
Shows marked "hidden" in data/podcasts.json stay hidden.
"""
import base64
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'podcasts.json')


def token(cid, secret, refresh):
    body = urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh}).encode()
    auth = base64.b64encode(f'{cid}:{secret}'.encode()).decode()
    req = urllib.request.Request('https://accounts.spotify.com/api/token', data=body,
                                 headers={'Authorization': f'Basic {auth}', 'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)['access_token']


def main():
    cid, secret, refresh = (os.environ.get(k, '').strip() for k in ('SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REFRESH_TOKEN'))
    if not (cid and secret and refresh):
        print('Spotify secrets not set; skipping Spotify')
        return
    try:
        access = token(cid, secret, refresh)
    except Exception as e:
        print(f'Spotify token refresh failed: {e}', file=sys.stderr)
        return
    shows, url = [], 'https://api.spotify.com/v1/me/shows?limit=50'
    while url:
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access}'})
        with urllib.request.urlopen(req, timeout=30) as r:
            page = json.load(r)
        for it in page.get('items', []):
            s = it['show']
            shows.append({'name': s['name'], 'publisher': s.get('publisher', ''), 'url': s['external_urls']['spotify'], 'added': it.get('added_at', '')[:10]})
        url = page.get('next')

    old = {}
    if os.path.exists(DATA):
        old = {s['url']: s for s in json.load(open(DATA, encoding='utf-8')).get('shows', [])}
    for s in shows:
        s['hidden'] = old.get(s['url'], {}).get('hidden', False)
    shows.sort(key=lambda s: s['added'], reverse=True)
    json.dump({'note': 'Synced from Spotify. Set "hidden": true to keep a show off the page.', 'shows': shows},
              open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'Spotify: {len(shows)} shows')


if __name__ == '__main__':
    main()
