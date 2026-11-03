"""Each golf page's story is worked out from the data, says only what the data shows, and
leaves a beat out rather than guessing when the data is missing (golf_story.py)."""
import copy
import json
import unittest
from datetime import date
from pathlib import Path

import golf_goals
import golf_story as story

ROOT = Path(__file__).resolve().parents[1]
STATS = json.loads((ROOT / 'data' / 'golf-stats.json').read_text())
GHIN = json.loads((ROOT / 'data' / 'golf.json').read_text())

# Words that would turn a description into coaching. What to change belongs to his coach.
ADVICE = ('should', 'try ', 'you need', 'work on', 'focus on', 'make sure', 'keep your')


def text(beats):
    return ' '.join(lead + ' ' + detail for lead, detail in beats)


def hole(score, par=4, pen=0, gir=False, putts=2):
    return {'score': score, 'par': par, 'pen': pen, 'gir': gir, 'putts': putts}


class EveryPage(unittest.TestCase):
    def pages(self):
        return [story.overview(STATS, GHIN), story.driving(STATS), story.approach(STATS),
                story.short_game(STATS), story.putting(STATS), story.rounds(STATS, GHIN)]

    def test_every_page_has_a_story_and_none_of_it_is_advice(self):
        for beats in self.pages():
            self.assertTrue(beats)
            words = text(beats).lower()
            for word in ADVICE:
                self.assertNotIn(word, words)

    def test_putting_never_reads_the_second_putt(self):
        # The site says later-putt positions are not reliable enough to diagnose lag leaves, so the
        # lag table in golf-stats.json stays out of the story even though it is in the file.
        lag = STATS['putting'].get('lag') or {}
        words = text(story.putting(STATS))
        for band in lag.values():
            self.assertNotIn(f'{band["avg_leave_ft"]} ft', words)
        self.assertIn('Only the first putt is measured', words)


class Ranges(unittest.TestCase):
    def test_a_range_that_includes_zero_is_not_settled(self):
        self.assertIn('not settled', story.settled([-3.2, 0.3]))
        self.assertIn('all below zero', story.settled([-5.3, -0.9]))
        self.assertIn('no uncertainty range', story.settled(None))

    def test_thin_bands_never_become_the_approach_loss(self):
        stats = copy.deepcopy(STATS)
        for band in stats['approach']['buckets'].values():
            band.update(thin=True, ci=[-2, -1])
        lead, _ = story.approach_band_beat(stats)
        self.assertEqual(lead, 'No distance band clearly loses on its own.')

    def test_touching_bands_read_as_one_range(self):
        self.assertEqual(story.span(['100-125', '75-100', '125-150'], 'yd'), '75 to 150 yd')
        self.assertEqual(story.span(['50-75', '125-150'], 'yd'), '50–75 and 125–150 yd')
        # a thin band in the gap does not break the range, an opposite band does
        self.assertEqual(story.outer_span(['0-3', '5-10', '10-15'], ['15-25'], 'ft'), '0 to 15 ft')
        self.assertEqual(story.outer_span(['0-3', '10-15'], ['5-10'], 'ft'), '0–3 and 10–15 ft')


class Holes(unittest.TestCase):
    def test_doubles_are_counted_from_the_scorecards(self):
        stats = {'rounds': [{'date': '2026-05-01', 'card': [
            hole(6, pen=1), hole(7, putts=3), hole(4, gir=True), hole(5), hole(6)]}]}
        lead, detail = story.doubles_beat(stats)
        self.assertEqual(lead, '3 doubles or worse made 7 of my 8 strokes over par.')
        self.assertIn('a penalty stroke was on 1, 3 missed the green and 1 had a three-putt', detail)

    def test_no_doubles_no_beat(self):
        self.assertIsNone(story.doubles_beat({'rounds': [{'date': '2026-05-01', 'card': [hole(4), hole(5)]}]}))


class Index(unittest.TestCase):
    def test_a_change_names_the_rounds_just_before_it(self):
        g = {'revisions': [{'date': '2026-10-01', 'index': '4.6'}, {'date': '2026-10-24', 'index': '4.6'},
                           {'date': '2026-10-25', 'index': '4.1'}],
             'recent_rounds': [{'date': '2026-10-24', 'score': 75, 'differential': 2.6},
                               {'date': '2026-09-01', 'score': 80, 'differential': 6.0}]}
        lead, detail = story.index_beat(g)
        self.assertEqual(lead, 'Index 4.1, down 0.5 on Oct 25.')
        self.assertIn('a 75 on Oct 24 (differential 2.6)', detail)
        self.assertNotIn('Sep', detail)

    def test_a_plus_handicap_moves_the_right_way(self):
        g = {'revisions': [{'date': '2026-10-01', 'index': '0.4'}, {'date': '2026-10-25', 'index': '+0.6'}]}
        self.assertEqual(story.index_beat(g)[0], 'Index +0.6, down 1.0 on Oct 25.')


class TrackMan(unittest.TestCase):
    TM = {'sessions_30d': 2, 'balls_30d': 120,
          'sessions': [{'date': '2026-11-02', 'drill': {'name': 'Pause at the top', 'balls': 35}},
                       {'date': '2026-09-01', 'drill': {'name': 'Pause at the top', 'balls': 40}}],
          'clubs': [{'club': 'Dr', 'carry': 298, 'last': '2026-10-29', 'side_spread': 22.1},
                    {'club': '7i', 'carry': 184, 'last': '2026-10-29', 'side_spread': 7.1},
                    {'club': '6i', 'carry': 194, 'last': '2026-10-30', 'side_spread': 16.3},
                    {'club': '5i', 'carry': 190, 'last': '2026-10-30', 'side_spread': 17.7}]}

    def beats(self):
        return story.trackman(self.TM, None, ['Dr', '5i', '6i', '7i'], today=date(2026, 11, 3))

    def test_only_drill_swings_inside_30_days_are_counted(self):
        self.assertIn('35 of them were drill swings', text(self.beats()))

    def test_gaps_are_read_down_the_bag_and_an_overlap_is_named(self):
        words = text(self.beats())
        self.assertIn('Widest: Driver to 5-iron, 108 yd.', words)
        self.assertIn('The 6-iron carries 4 yd past the 5-iron.', words)

    def test_without_tour_numbers_the_driver_comparison_is_left_out(self):
        self.assertNotIn('PGA', text(self.beats()))


class GoalStanding(unittest.TestCase):
    GOAL = {'target': 315, 'unit': 'yd', 'analysis': {'reviewed': '2026-10-29', 'ranges': [
        {'key': 'ball_speed', 'label': 'Ball speed', 'unit': 'mph', 'range': '180–183 mph'},
        {'key': 'launch', 'label': 'Launch', 'unit': '°', 'range': '13–15°'},
        {'key': 'spin', 'label': 'Spin', 'unit': 'rpm', 'range': '2,000–2,400 rpm'}]}}

    def test_each_number_is_placed_against_its_working_range(self):
        html = golf_goals.standing(self.GOAL, {'date': '2026-11-02', 'ball_speed': 171.2, 'launch': 13.6,
                                               'spin': 2595.8})
        self.assertIn('1 of 3 launch numbers sit inside the working range for 315 yd.', html)
        self.assertIn('<b>Ball speed 171.2 mph.</b> Under the working range of 180–183 mph.', html)
        self.assertIn('<b>Spin 2,596 rpm.</b> Over the working range', html)
        self.assertIn('<b>Launch 13.6°.</b> Inside', html)

    def test_no_session_no_story(self):
        self.assertEqual(golf_goals.standing(self.GOAL, {}), '')


class GradeWords(unittest.TestCase):
    GRADE = {'grader': 2, 'summary': 'missed all 2', 'ungraded': ['Warmup: warm-up, no target'], 'results': [
        {'what': 'Driver corridor', 'measured': '55% inside \u00b118 yd', 'n': 11, 'pass': False, 'target': '65%'},
        {'what': 'Driver carry', 'measured': 'median 293 yd, best 299, 116.9 mph club', 'n': 11, 'pass': False,
         'target': '315 yd'}]}

    def test_each_check_says_what_was_measured_and_what_it_needed(self):
        self.assertEqual(story.grade_lines(self.GRADE), [
            'Driver corridor: 6 of 11 inside \u00b118 yd (55%); needs 65%. Not met.',
            'Driver carry: median 293 yd, best 299, 116.9 mph club, 11 shots; needs 315 yd. Not met.'])
        self.assertEqual(story.grade_tally(self.GRADE), '0 of 2 met')

    def test_a_session_with_nothing_checkable_says_so(self):
        g = {'results': [], 'summary': 'not gradeable', 'ungraded': ['Technical: a drill']}
        self.assertEqual(story.grade_tally(g), 'not graded')
        self.assertTrue(story.grade_lines(g)[0].startswith('Nothing graded'))

    def test_an_old_string_grade_still_reads(self):
        self.assertEqual(story.grade_lines('met 2 of 5'), ['met 2 of 5'])


class DriverHeadline(unittest.TestCase):
    """Road to 315 heads with the last 20 drives (Jack, 2026-11-02), not one session's median."""

    def goal(self):
        return golf_goals.load_goals(ROOT)[0]

    def tm(self, form_n=20):
        return {'driver': {'carry': 289, 'n': form_n, 'ball_speed': 171.3},
                'session_stats': [{'id': 'a', 'date': '2026-11-02', 'clubs': [
                    {'club': 'Dr', 'carry': 293, 'carry_best': 299.7, 'n': 11, 'ball_speed': 171.2}]}]}

    def test_the_headline_and_the_gap_use_the_last_20_drives(self):
        html = golf_goals.section(self.goal(), self.tm())
        self.assertIn('Median carry · last 20 drives</span><strong>289 yd</strong>', html)
        self.assertIn('Latest session · Nov 2</span><strong>293 yd</strong>', html)
        self.assertIn('Gap to goal</span><strong>26 yd</strong>', html)
        self.assertIn('289 yd <small>', golf_goals.index([self.goal()], self.tm()))

    def test_too_few_drives_falls_back_to_the_session(self):
        html = golf_goals.section(self.goal(), self.tm(form_n=5))
        self.assertIn('<strong>293 yd</strong>', html)
        self.assertNotIn('last 5 drives', html)

    def test_the_driving_story_quotes_the_same_number(self):
        self.assertIn('289 yd carry in practice', text(story.driving(STATS, self.tm())))


if __name__ == '__main__':
    unittest.main()
