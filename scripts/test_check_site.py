"""Make sure the publication check rejects broken pages, not just today's site."""
import tempfile
from pathlib import Path
import unittest
from check_site import check


class SiteChecks(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.page = '<html lang="en"><meta name="robots" content="noindex"><meta name="viewport" content="width=device-width"><h1 id="main">Test</h1>'
        (self.root / 'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')

    def run_page(self, content):
        (self.root / 'index.html').write_text(content)
        return check(self.root)[1]

    def test_valid_page(self):
        self.assertEqual(self.run_page(self.page + '<a href="#main">Content</a>'), [])

    def test_broken_destination_anchor_and_accessible_reference(self):
        errors = self.run_page(self.page + '<a href="missing.pdf">File</a><a href="#absent">Jump</a><input aria-describedby="missing-help">')
        self.assertEqual(len(errors), 3)
        self.assertTrue(any('missing anchor' in e for e in errors))

    def test_stale_asset(self):
        (self.root / 'test.js').write_text('test')
        errors = self.run_page(self.page + '<script src="test.js?v=old"></script>')
        self.assertEqual(len(errors), 1)
        self.assertIn('stale asset', errors[0])


if __name__ == '__main__':
    unittest.main()
