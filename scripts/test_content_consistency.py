"""Cross-page facts and regressions for generated writing summaries."""
import html
import json
from pathlib import Path
import re
import tempfile
import unittest
from build_dca import update_writing_blurb
from build_facts import derived_facts

ROOT = Path(__file__).resolve().parents[1]


class ContentConsistency(unittest.TestCase):
    def test_writing_update_handles_multiline_json_and_preserves_other_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'writing.json'
            data = {'items': [{'dek': 'old', 'url': 'bitcoin-dca.html'}, {'url': 'other.html', 'dek': 'keep'}]}
            path.write_text(json.dumps(data, indent=2))
            update_writing_blurb(path, '$10 in, $20 out')
            actual = json.loads(path.read_text())
            self.assertEqual(actual['items'][0]['dek'], '$10 in, $20 out')
            self.assertEqual(actual['items'][1], data['items'][1])
            before = path.read_bytes()
            update_writing_blurb(path, '$10 in, $20 out')
            self.assertEqual(path.read_bytes(), before)

    def test_missing_writing_entry_does_not_silently_succeed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'writing.json'
            path.write_text('{"items": []}')
            with self.assertRaises(ValueError):
                update_writing_blurb(path, 'new')

    def test_shared_fact_spans_match_source(self):
        facts = json.loads((ROOT / 'data/facts.json').read_text())
        facts.update(derived_facts())
        for file in list(ROOT.glob('*.html')) + list(ROOT.glob('notes/*.html')):
            for key, value in re.findall(r'<span data-fact="([^"]+)">(.*?)</span>', file.read_text(), re.S):
                with self.subTest(page=file.name, fact=key):
                    self.assertIn(key, facts)
                    self.assertEqual(html.unescape(value), html.unescape(facts[key]))

    def test_dca_summary_matches_shared_facts_and_published_surfaces(self):
        facts = json.loads((ROOT / 'data/facts.json').read_text())
        expected = f'{facts["dca.put_in"]} in, about {facts["dca.value"]} out, and two drops of more than 75% along the way.'
        data = json.loads((ROOT / 'data/writing.json').read_text())
        item = next(i for i in data['items'] if i['url'] == 'bitcoin-dca.html')
        self.assertEqual(item['dek'], expected)
        for name in ('index.html', 'bitcoin-dca.html', 'writing.html', 'feed.xml'):
            with self.subTest(page=name):
                self.assertIn(expected, html.unescape((ROOT / name).read_text()))


if __name__ == '__main__':
    unittest.main()
