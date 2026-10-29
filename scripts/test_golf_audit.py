"""Regressions for source distinctions and statistical interpretation."""
import copy
import json
from pathlib import Path
import unittest
import build_golf as golf

ROOT = Path(__file__).resolve().parents[1]

class GolfAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = json.loads((ROOT / 'data/golf-stats.json').read_text())
        cls.ghin = json.loads((ROOT / 'data/golf.json').read_text())

    def test_score_and_strokes_gained_have_opposite_good_signs(self):
        self.assertIn('class="neg">+2.0', golf.over_par(2))
        self.assertIn('class="pos">+2.0', golf.sg(2))
        self.assertIn('class="pos">-2.0', golf.over_par(-2))

    def test_interval_touching_zero_is_not_decisive(self):
        for ci in (None, [-1, 0], [0, 1], [-1, 1]):
            self.assertFalse(golf.decisive(ci))
        self.assertTrue(golf.decisive([-2, -1]))

    def test_handicap_chart_handles_scratch_and_plus(self):
        for index in (0, '+1.5'):
            html = golf.chart([{'date': '2026-10-29', 'index': index}], '2026-10-29')
            self.assertIn('<svg', html)
            self.assertNotIn('nan', html)

    def test_thin_putting_bucket_cannot_become_a_diagnosis(self):
        stats = copy.deepcopy(self.stats)
        for bucket in stats['putting']['buckets'].values():
            bucket.update(thin=True, ci=[-2, -1])
        html = golf.page_putting(stats, self.ghin)
        self.assertIn('keep measuring', html)
        self.assertIn('first putts', html)
        self.assertIn('percentage points', html)
        self.assertIn('Later putts remain', html)

    def test_full_wedge_carry_does_not_grade_short_chips(self):
        tm = {'clubs': [{'club': '58°', 'carry_spread': 3}]}
        self.assertFalse(golf._loop_rows(tm, {'leaks': [{'name': '0-20 yd short game', 'per_round': -2}]}))

    def test_scorecard_totals_reconcile(self):
        stats = self.stats
        self.assertEqual(sum(len(r['card']) for r in stats['rounds']), stats['holes'])
        for rnd in stats['rounds']:
            self.assertEqual(sum(h['score'] for h in rnd['card']), rnd['score'])

    def test_state_rank_is_not_a_national_public_rank(self):
        courses = json.loads((ROOT / 'data/courses.json').read_text())['courses']
        for course in courses:
            if course['name'].startswith(('Torrey Pines Golf Course - North', 'Trump National Golf Club', 'PGA West - Nicklaus')):
                self.assertNotIn('rank', course)

    def test_all_golf_pages_explain_sources_and_keep_private_data_out(self):
        for filename, _ in golf.PAGES:
            text = (ROOT / filename).read_text()
            self.assertEqual(text.count('<h1>'), 1, filename)
            self.assertIn('How to read these pages', text)
            self.assertIn('2026-04-15 to 2026-06-04', text)
            for private in ('/Users/jack/', '.openclaw', '66d756124ee3', 'Trackman Data 10-29-26.csv'):
                self.assertNotIn(private, text)

if __name__ == '__main__':
    unittest.main()
