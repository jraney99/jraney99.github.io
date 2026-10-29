"""Partial-bag TrackMan sessions must not replace unhit clubs with invented data."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_golf as golf


class PartialBag(unittest.TestCase):
    def test_goal_history_survives_empty_recent_window(self):
        tm = {'clubs': [], 'session_stats': [{'id': 'old', 'date': '2026-10-29', 'clubs': []}]}
        with tempfile.TemporaryDirectory() as root:
            data = Path(root) / 'data'
            data.mkdir()
            (data / 'trackman.json').write_text(json.dumps(tm))
            with patch.object(golf, 'ROOT', root):
                self.assertIsNone(golf.trackman_data())
                self.assertEqual(golf.trackman_data(include_history=True), tm)

    def render(self, clubs):
        tm = {'clubs': clubs, 'wedges': [], 'sessions': [], 'sessions_n': 1,
              'balls_total': 10, 'units': {'dist': 'yd', 'speed': 'mph'}}
        before = copy.deepcopy(tm)
        with patch.object(golf, 'plans_cards', return_value=''), \
             patch.object(golf, 'bag_card', return_value=''), \
             patch.object(golf, 'tour_mark', return_value=None), \
             patch.object(golf, '_loop_rows', return_value='') as loop:
            html = golf.page_trackman_real(tm, {})
        self.assertEqual(tm, before)
        self.assertEqual(loop.call_args[0][0]['clubs'], clubs)
        return html

    def test_measured_carry_replaces_only_that_club(self):
        html = self.render([{'club': '7i', 'carry': 184, 'carry_spread': 6, 'n': 10}])
        gap = html.split('Gapping: carry per club', 1)[1].split('</ul>', 1)[0]
        rows = re.findall(r'<li\b.*?</li>', gap, flags=re.S)
        self.assertEqual(len(rows), len(golf.SAMPLE_GAPPING))
        measured = next(r for r in rows if '>7i<' in r)
        self.assertIn('184', measured)
        self.assertIn('10 shots', measured)
        self.assertNotIn('Sample', measured)
        for club, carry, _ in golf.SAMPLE_GAPPING:
            if club == '7i':
                continue
            row = next(r for r in rows if '>%s<' % club in r)
            self.assertIn(str(carry), row)
            self.assertIn('Sample · not yet measured', row)

    def test_real_club_without_side_data_does_not_inherit_sample_dispersion(self):
        html = self.render([{'club': 'Dr', 'carry': 298, 'n': 10}])
        dispersion = html.split('Dispersion: left-right spread', 1)[1].split('</ul>', 1)[0]
        self.assertNotIn('>Dr<', dispersion)
        self.assertIn('>3w<', dispersion)
        self.assertIn('Sample · not yet measured', dispersion)


if __name__ == '__main__':
    unittest.main()
