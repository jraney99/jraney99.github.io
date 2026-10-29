"""Validate public pages before publishing. Uses only the Python standard library."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import hashlib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    @property
    def ids(self):
        return [a['id'] for _, a in self.tags if a.get('id')]


def check(root=ROOT):
    pages = {p: Page(p.read_text()) for p in sorted(root.glob('*.html')) + sorted(root.glob('notes/*.html'))}
    errors = []
    canonicals = set()
    def require(ok, file, message):
        if not ok:
            errors.append(f'{file.relative_to(root)}: {message}')
    for file, page in pages.items():
        metas = {a.get('name', a.get('property')): a.get('content') for t, a in page.tags if t == 'meta'}
        require(sum(t == 'h1' for t, _ in page.tags) == 1, file, 'expected one main heading')
        require(bool(metas.get('viewport')), file, 'missing viewport')
        require(not any(n > 1 for n in Counter(page.ids).values()), file, 'duplicate IDs')
        require(any(t == 'html' and a.get('lang') for t, a in page.tags), file, 'missing document language')
        if 'noindex' not in metas.get('robots', ''):
            for name in ('description', 'og:title', 'og:description', 'og:url', 'og:image', 'twitter:card'):
                require(bool(metas.get(name)), file, f'missing {name}')
            canonical = [a.get('href') for t, a in page.tags if t == 'link' and a.get('rel') == 'canonical']
            require(canonical == [metas.get('og:url')], file, 'canonical and share URL differ')
            if canonical:
                require(canonical[0] not in canonicals, file, 'duplicate canonical URL')
                canonicals.add(canonical[0])
        links = []
        for tag, a in page.tags:
            if tag == 'img':
                require('alt' in a, file, 'image missing alt text')
            if tag in ('a', 'link', 'script', 'img', 'source', 'audio'):
                links.extend(a[k] for k in ('href', 'src') if a.get(k))
            if tag == 'meta' and a.get('property') == 'og:image':
                links.append(a.get('content', ''))
            for ref in ('aria-labelledby', 'aria-describedby'):
                for target in a.get(ref, '').split():
                    require(target in page.ids, file, f'{ref} points to missing #{target}')
        for link in links:
            url = urlsplit(link)
            if url.netloc and url.netloc != 'jackraney.com':
                continue
            if url.scheme and url.scheme not in ('https', 'http'):
                continue
            dest = root / unquote(url.path).lstrip('/') if url.path.startswith('/') or url.netloc else file.parent / unquote(url.path)
            if not url.path:
                dest = file
            if dest.is_dir():
                dest = dest / 'index.html' if (dest / 'index.html').is_file() else dest.with_suffix('.html')
            if not dest.exists() and not dest.suffix:
                dest = dest.with_suffix('.html')
            require(dest.is_file(), file, f'missing destination: {link}')
            if url.fragment and dest in pages:
                require(unquote(url.fragment) in pages[dest].ids, file, f'missing anchor: {link}')
            if dest.is_file() and dest.suffix in ('.js', '.css') and url.query.startswith('v='):
                require(url.query[2:] == hashlib.sha256(dest.read_bytes()).hexdigest()[:10], file, f'stale asset: {link}')
    sitemap = {node.text for node in ET.parse(root / 'sitemap.xml').iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')}
    # Detailed golf pages are deliberately unlisted, per Jack's preference.
    expected = {url for url in canonicals if not urlsplit(url).path.startswith('/golf-')}
    require(sitemap == expected, root / 'sitemap.xml', 'sitemap differs from indexable canonical pages')
    return len(pages), errors


if __name__ == '__main__':
    count, errors = check()
    for error in errors:
        print(error)
    print(f'{count} pages checked; {len(errors)} errors.')
    raise SystemExit(bool(errors))
