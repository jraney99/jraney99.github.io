"""Rebuild resume/Jack-Raney-Resume.pdf when resume.html changes.

Prints the page with headless Chrome. Skips the work if resume.html is unchanged
since the last build (hash in resume/.source-hash). If the new PDF is not exactly
one page, the old PDF is kept and the script exits non-zero so the change gets looked at.
Set CHROME to the browser binary if it is not on the default path.
"""
import hashlib
import http.server
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import functools

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'resume.html')
PDF = os.path.join(ROOT, 'resume', 'Jack-Raney-Resume.pdf')
HASH = os.path.join(ROOT, 'resume', '.source-hash')
CANDIDATES = [os.environ.get('CHROME', ''), 'google-chrome', 'chromium',
              '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']


def chrome():
    for c in CANDIDATES:
        if c and (shutil.which(c) or os.path.exists(c)):
            return shutil.which(c) or c
    sys.exit('No Chrome found; set CHROME.')


def main():
    digest = hashlib.sha256(open(SRC, 'rb').read()).hexdigest()
    if os.path.exists(HASH) and open(HASH).read().strip() == digest and os.path.exists(PDF):
        print('résumé unchanged; PDF left as is')
        return
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=ROOT)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    out = os.path.join(tempfile.mkdtemp(), 'resume.pdf')
    try:
        subprocess.run([chrome(), '--headless=new', '--disable-gpu', '--no-sandbox', '--no-pdf-header-footer',
                        '--virtual-time-budget=8000', f'--print-to-pdf={out}',
                        f'http://127.0.0.1:{srv.server_address[1]}/resume.html'],
                       check=True, capture_output=True, timeout=120)
    finally:
        srv.shutdown()
    pages = re.findall(rb'/Count (\d+)', open(out, 'rb').read())
    count = int(pages[0]) if pages else 0
    if count != 1:
        print(f'::warning::résumé renders to {count} pages; kept the previous PDF. Shorten resume.html.')
        sys.exit(1)
    shutil.copyfile(out, PDF)
    open(HASH, 'w').write(digest + '\n')
    print('résumé PDF rebuilt (1 page)')


if __name__ == '__main__':
    main()
