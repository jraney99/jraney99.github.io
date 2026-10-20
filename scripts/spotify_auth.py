"""One-time setup: connect Spotify so the reading page can list the podcasts you follow.

Run it yourself, in Terminal, from the site folder:
    python3 scripts/spotify_auth.py

It asks for your Spotify app's Client ID and Client secret, opens Spotify in your
browser to approve read-only access (the shows you follow, nothing else), then saves
SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET and SPOTIFY_REFRESH_TOKEN as GitHub secrets
on the site repo with the gh CLI. Nothing is printed or written to disk.

Before running: at developer.spotify.com/dashboard, create an app with the redirect
URI http://127.0.0.1:8888/callback and "Web API" ticked.
"""
import base64
import getpass
import http.server
import json
import secrets
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser

REPO = 'jraney99/jraney99.github.io'
REDIRECT = 'http://127.0.0.1:8888/callback'

cid = input('Spotify Client ID: ').strip()
csecret = getpass.getpass('Spotify Client secret (hidden as you type): ').strip()
if not cid or not csecret:
    sys.exit('Both the Client ID and the Client secret are needed.')

state = secrets.token_urlsafe(16)
result = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        ok = q.get('state', [''])[0] == state and 'code' in q
        result['code'] = q['code'][0] if ok else None
        result['error'] = q.get('error', [''])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Done. You can close this tab and go back to Terminal.' if ok else b'Something went wrong. Go back to Terminal.')

    def log_message(self, *a):
        pass


url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode(
    {'client_id': cid, 'response_type': 'code', 'redirect_uri': REDIRECT, 'scope': 'user-library-read', 'state': state})
print('\nOpening Spotify in your browser. Click "Agree" to allow read-only access.')
webbrowser.open(url)
http.server.HTTPServer(('127.0.0.1', 8888), Handler).handle_request()
if not result.get('code'):
    sys.exit(f'Spotify did not approve the request ({result.get("error") or "no code"}). Check the redirect URI and try again.')

body = urllib.parse.urlencode({'grant_type': 'authorization_code', 'code': result['code'], 'redirect_uri': REDIRECT}).encode()
auth = base64.b64encode(f'{cid}:{csecret}'.encode()).decode()
req = urllib.request.Request('https://accounts.spotify.com/api/token', data=body,
                             headers={'Authorization': f'Basic {auth}', 'Content-Type': 'application/x-www-form-urlencoded'})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        refresh = json.load(r)['refresh_token']
except Exception as e:
    sys.exit(f'Could not get a token from Spotify: {e}. Double-check the Client secret.')

# Quick check that the token works before saving anything.
tok_req = urllib.request.Request('https://accounts.spotify.com/api/token',
                                 data=urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh}).encode(),
                                 headers={'Authorization': f'Basic {auth}', 'Content-Type': 'application/x-www-form-urlencoded'})
with urllib.request.urlopen(tok_req, timeout=30) as r:
    access = json.load(r)['access_token']
with urllib.request.urlopen(urllib.request.Request('https://api.spotify.com/v1/me/shows?limit=50',
                                                   headers={'Authorization': f'Bearer {access}'}), timeout=30) as r:
    count = json.load(r).get('total', 0)
print(f'Connected. Spotify shows you follow: {count}')

for name, value in (('SPOTIFY_CLIENT_ID', cid), ('SPOTIFY_CLIENT_SECRET', csecret), ('SPOTIFY_REFRESH_TOKEN', refresh)):
    done = subprocess.run(['gh', 'secret', 'set', name, '-R', REPO], input=value, text=True, capture_output=True)
    if done.returncode != 0:
        sys.exit(f'Saving {name} to GitHub failed: {done.stderr.strip()}')
    print(f'Saved {name} to GitHub')

print('\nAll set. The podcasts will appear on the reading page after the next daily update.')
