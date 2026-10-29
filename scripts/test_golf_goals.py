import copy
import unittest
from pathlib import Path

import golf_goals as goals


class Goals(unittest.TestCase):
    def setUp(self):
        self.goal = goals.load_goals(Path(__file__).resolve().parents[1])[0]

    def session(self, day, carry=298, n=10, club='Dr', **extra):
        row = dict(club=club, carry=carry, carry_best=304, n=n, ball_speed=171.1, corridor_pct=60)
        row.update(extra)
        return {'id': day, 'date': day, 'clubs': [row]}

    def render(self, *sessions):
        return goals.section(self.goal, {'session_stats': list(sessions)})

    def test_no_history_does_not_use_preview_or_rolling_aggregate(self):
        html = goals.section(self.goal, {'clubs': [{'club': 'Dr', 'carry': 282}]})
        self.assertIn('Awaiting a baseline', html)
        self.assertNotIn('282 yd', html)
        self.assertIn('Preview numbers are never used', html)

    def test_one_session_is_a_baseline_not_a_trend_line(self):
        html = self.render(self.session('2026-10-29'))
        self.assertIn('298 yd', html)
        self.assertIn('17 yd', html)
        self.assertIn('baseline, not a trend', html)
        self.assertNotIn('<polyline', html)
        self.assertEqual(html.count('<circle'), 1)

    def test_new_session_updates_headline_and_history(self):
        html = self.render(self.session('2026-10-29'), self.session('2026-11-02', carry=307, ball_speed=178))
        self.assertIn('307 yd', html)
        self.assertIn('8 yd', html)
        self.assertIn('+9.0 yd', html)
        self.assertIn('178 mph', html)
        self.assertIn('<polyline', html)
        self.assertIn('Analysis reviewed 2026-10-29', html)

    def test_unhit_club_does_not_create_progress_point(self):
        html = self.render(self.session('2026-10-29'), self.session('2026-11-02', carry=180, club='7i'))
        self.assertIn('Latest qualifying session: 2026-10-29', html)
        self.assertEqual(html.count('<circle'), 1)

    def test_small_sample_cannot_claim_goal_or_change_headline(self):
        html = self.render(self.session('2026-10-29'), self.session('2026-11-02', carry=330, n=3))
        self.assertIn('small sample', html)
        self.assertIn('Latest qualifying session: 2026-10-29', html)
        self.assertNotIn('Target met this session', html)
        self.assertEqual(html.count('<circle'), 1)

    def test_goal_met_is_session_specific_and_gap_is_not_negative(self):
        html = self.render(self.session('2026-11-02', carry=317))
        self.assertIn('Target met this session', html)
        self.assertIn('does not yet establish repeatability', html)
        self.assertIn('<strong>0 yd</strong>', html)
        self.assertNotIn('-2 yd', html)

    def test_registry_routes_future_goals_without_duplicate_page_sections(self):
        second = copy.deepcopy(self.goal)
        second.update(id='wedge-carry', title='Wedge carry', club='Pw', page='golf-approach.html', category='Approach')
        registry = [self.goal, second]
        idx = goals.index(registry, {})
        self.assertIn('golf-driving.html#road-to-315', idx)
        self.assertIn('golf-approach.html#wedge-carry', idx)
        driving = goals.for_page('golf-driving.html', registry, {})
        self.assertIn('id="road-to-315"', driving)
        self.assertNotIn('id="wedge-carry"', driving)

    def test_missing_optional_fields_are_not_zero_and_text_is_escaped(self):
        goal = dict(self.goal, title='<script>alert(1)</script>')
        html = goals.section(goal, {'session_stats': [{'id': 'x', 'date': '2026-10-29',
                                                     'clubs': [{'club': 'Dr', 'carry': 298, 'n': 10}]}]})
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('<td>—</td>', html)


if __name__ == '__main__':
    unittest.main()
