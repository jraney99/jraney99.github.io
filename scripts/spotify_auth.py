"""One-time helper: get a Spotify refresh token for the reading-page sync.

Run it yourself on your own computer:
  1. At developer.spotify.com/dashboard, create an app. Add the redirect URI
     http://127.0.0.1:8888/callback and tick "Web API".
  2. SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... python3 scripts/spotify_auth.py
  3. Approve in the browser window that opens.
  4. Copy the refresh token it prints into the repo's GitHub secrets as
     SPOTIFY_REFRESH_TOKEN (and the ID and secret as SPOTIFY_CLIENT_ID and
     SPOTIFY_CLIENT_SECRET). Don't commit it or paste it anywhere else.
The only permission requested is user-library-read (the shows you follow).
"""
import base64
import http.server
import json
import os
import secrets
import urllib.parse
import urllib.request
import webbrowser

REDIRECT = 'http://127.0.0.1:8888/callback'
cid, csecret = os.environ['SPOTIFY_CLIENT_ID'], os.environ['SPOTIFY_CLIENT_SECRET']
state = secrets.token_urlsafe(16)
result = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        ok = q.get('state', [''])[0] == state and 'code' in q
        result['code'] = q['code'][0] if ok else None
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Done. You can close this tab.' if ok else b'Something went wrong. Try again.')

    def log_message(self, *a):
        pass


url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode(
    {'client_id': cid, 'response_type': 'code', 'redirect_uri': REDIRECT, 'scope': 'user-library-read', 'state': state})
print('Opening Spotify to approve read-only access...')
webbrowser.open(url)
http.server.HTTPServer(('127.0.0.1', 8888), Handler).handle_request()
if not result.get('code'):
    raise SystemExit('No authorization code received.')
body = urllib.parse.urlencode({'grant_type': 'authorization_code', 'code': result['code'], 'redirect_uri': REDIRECT}).encode()
auth = base64.b64encode(f'{cid}:{csecret}'.encode()).decode()
req = urllib.request.Request('https://accounts.spotify.com/api/token', data=body,
                             headers={'Authorization': f'Basic {auth}', 'Content-Type': 'application/x-www-form-urlencoded'})
with urllib.request.urlopen(req, timeout=30) as r:
    tok = json.load(r)
print('\nSPOTIFY_REFRESH_TOKEN =', tok['refresh_token'])
