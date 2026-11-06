"""The TrackMan tab: one table by club, each number shown once, and partial-bag sessions never
replacing unhit clubs with invented data."""
import copy
import json
import re
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import build_golf as golf


def rows_of(html):
    body = html.split('By club', 1)[1].split('</tbody>', 1)[0]
    return re.findall(r'<tr\b.*?</tr>', body.split('<tbody>', 1)[1], flags=re.S)


def row_for(rows, name):
    return next(r for r in rows if re.search(r'<td>%s( <small>|</td>)' % re.escape(name), r))


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

    def render(self, clubs, **extra):
        tm = {'clubs': clubs, 'wedges': [], 'sessions': [], 'sessions_n': 1,
              'balls_total': 10, 'units': {'dist': 'yd', 'speed': 'mph'}, **extra}
        before = copy.deepcopy(tm)
        with patch.object(golf, 'plans_data', return_value=[]), \
             patch.object(golf, 'session_days', return_value=[]), \
             patch.object(golf, 'bag_card', return_value=''), \
             patch.object(golf, 'tour_mark', return_value=None), \
             patch.object(golf.golf_goals, 'load_goals', return_value=[]):
            html = golf.page_trackman_real(tm, {})
        self.assertEqual(tm, before)
        return html

    def test_measured_carry_replaces_only_that_club(self):
        rows = rows_of(self.render([{'club': '7i', 'carry': 184, 'carry_spread': 6, 'n': 10}]))
        self.assertEqual(len(rows), len(golf.SAMPLE_GAPPING))
        measured = row_for(rows, '7-iron')
        self.assertIn('>184<', measured)
        self.assertNotIn('sample', measured)
        for club, carry, _ in golf.SAMPLE_GAPPING:
            if club == '7i':
                continue
            row = row_for(rows, golf.golf_story.club_name(club))
            self.assertIn('>%d<' % carry, row)
            self.assertIn('<small>sample</small>', row)

    def test_real_club_without_side_data_does_not_inherit_sample_dispersion(self):
        rows = rows_of(self.render([{'club': 'Dr', 'carry': 298, 'n': 10}]))
        driver = row_for(rows, 'Driver')
        cells = re.findall(r'<td[^>]*>(.*?)</td>', driver)
        self.assertEqual(cells[-2:], ['–', '–'])          # no left/right spread, no miss side
        sample_3w = row_for(rows, '3-wood')
        self.assertIn('>19<', sample_3w)                             # the 3-wood is still a labeled sample

    def test_gap_to_next_club_is_read_down_the_bag(self):
        rows = rows_of(self.render([{'club': 'Dr', 'carry': 298, 'n': 10}, {'club': '3w', 'carry': 256, 'n': 10}]))
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_for(rows, 'Driver'))
        self.assertEqual(cells[5], '42')

    def test_total_sits_beside_carry_and_a_club_without_one_shows_a_dash(self):
        rows = rows_of(self.render([{'club': 'Dr', 'carry': 298, 'total': 314, 'n': 10},
                                    {'club': '3w', 'carry': 256, 'n': 10}]))
        self.assertEqual(re.findall(r'<td[^>]*>(.*?)</td>', row_for(rows, 'Driver'))[2:4], ['298', '314'])
        self.assertEqual(re.findall(r'<td[^>]*>(.*?)</td>', row_for(rows, '3-wood'))[3], '\u2013')

    def test_spread_wider_than_the_corridor_is_flagged(self):
        rows = rows_of(self.render([{'club': 'Dr', 'carry': 298, 'side_spread': 22.1, 'side_bias': 'straight'},
                                    {'club': '7i', 'carry': 184, 'side_spread': 7.1, 'side_bias': 'left'}]))
        self.assertIn('tm-flag">22.1<', row_for(rows, 'Driver'))
        self.assertNotIn('tm-flag', row_for(rows, '7-iron'))
        self.assertIn('<td>left</td>', row_for(rows, '7-iron'))

    def test_old_three_card_layout_is_gone_and_each_definition_appears_once(self):
        html = self.render([{'club': 'Dr', 'carry': 298, 'n': 10}])
        for gone in ('Gapping: carry per club', 'Dispersion: left-right spread', 'Wedge carries',
                     'Practice against play', 'Why it moved'):
            self.assertNotIn(gone, html)
        for term in golf.EXPLAIN:
            self.assertLessEqual(html.count('<b>%s.</b>' % golf.EXPLAIN[term][0]), 1, term)

    def test_corridor_below_target_is_the_only_gold_figure(self):
        form = {'carry': 288, 'n': 20, 'ball_speed': 170.8, 'smash': 1.48, 'corridor_pct': 55}
        html = self.render([{'club': 'Dr', 'carry': 298, 'n': 10}], driver=form, balls_30d=473, sessions_30d=8)
        strip = html.split('tm-figs', 1)[1].split('</dl>', 1)[0]
        self.assertEqual(strip.count('is-signal'), 1)
        self.assertIn('is-signal">55%', strip)
        self.assertIn('288 yd<small>last 20 drives', strip)
        self.assertIn('473 balls', strip)

    def test_moved_sentence_is_one_text_span_beside_the_pill(self):
        # 2026-11-06: the summary was a flex row, so every text run became its own spaced item.
        explain = {'driver': {'club': 'Driver', 'now_label': 'Nov 6', 'then_label': 'your measuring day (Oct 29)',
                              'sentence': 'Carried 10 yd less.', 'rows': [
                                  {'label': 'Carry', 'then': 297.9, 'now': 287.5, 'unit': 'yd'}]}}
        html = self.render([{'club': 'Dr', 'carry': 298, 'n': 10}], explain=explain)
        summary = re.search(r'<summary>(.*?)</summary>', html.split('tm-moved', 1)[1]).group(1)
        self.assertEqual(summary, '<span class="tm-pill">Moved</span><span class="tm-moved__text">'
                                  '<b>Driver, Nov 6.</b> Carried 10 yd less.</span>')
        self.assertIn('<th>Measuring day (Oct 29)</th>', html)


class LatestSession(unittest.TestCase):
    DAY = {'day': '2026-11-06', 'kind': 'Sim', 'sub': 'Nov 6 · 56 balls', 'status': '1 of 2 met',
           'lines': ['Driver corridor: 8 of 9 inside ±18 yd (89%); needs 70%. Met.',
                     'Driver carry: median 288 yd, best 292, 9 shots; needs 315 yd. Not met.'],
           'plan': None, 'ran': [{'balls': 56}]}
    STATS = {'leaks': [{'name': 'Driving penalties', 'per_round': -2.2}]}

    def test_each_check_says_met_or_not(self):
        html = golf.latest_session(self.STATS, [self.DAY], [])
        self.assertIn('<li class="tm-met"><span class="tm-dot" aria-hidden="true"></span><span><b>Driver corridor</b> '
                      '8 of 9 inside ±18 yd (89%); needs 70%.</span><span class="tm-res">Met</span></li>', html)
        self.assertIn('<li class="tm-unmet">', html)
        self.assertIn('<span class="tm-res">Not met</span>', html)
        self.assertIn('cost <b>2.2 strokes a round</b> on the course, my biggest leak.', html)

    def test_a_future_plan_is_shown_as_next_and_a_missed_one_says_so(self):
        ahead = (date.today() + timedelta(days=1)).isoformat()
        plan = {'date': ahead, 'type': 'sim', 'location': 'The Reserve', 'blocks': []}
        self.assertIn('Next: Sim session', golf.latest_session(self.STATS, [self.DAY], [plan]))
        day = dict(self.DAY, day='2026-11-01')
        missed = dict(plan, date='2026-11-03')
        self.assertIn('Planned for Nov 3 at The Reserve. No session recorded.',
                      golf.latest_session(self.STATS, [day], [missed]))

    def test_no_session_no_card(self):
        self.assertEqual(golf.latest_session(self.STATS, [dict(self.DAY, ran=[])], []), '')


class BagFold(unittest.TestCase):
    def test_identically_built_clubs_share_a_row(self):
        built = {'make': 'Ping', 'model': 'Blueprint T', 'shaft': 'Aerotech 110', 'flex': 'Stiff'}
        bag = {'clubs': [{'club': 'Driver', 'make': 'Ping', 'model': 'G430'},
                         dict(built, club='4 iron'), dict(built, club='5 iron'), dict(built, club='6 iron'),
                         dict(built, club='50°', loft='50°')]}
        with patch.object(golf, 'clubs_data', return_value=bag):
            html = golf.bag_card(fold=True)
        self.assertIn('<td>4 iron to 6 iron <small>Ping</small></td>', html)
        self.assertEqual(html.count('<tr>'), 4)  # header, driver, the irons, the wedge
        self.assertIn('<details class="gfold">', html)


if __name__ == '__main__':
    unittest.main()
