#!/usr/bin/env python3
"""Render the golf section: golf.html (hub) plus the deep pages, from data/golf.json
(written daily by Archibald's ghin-handicap skill) and data/golf-stats.json (computed
from sensor-tracked rounds; strokes gained vs a scratch baseline calibrated to Arccos).

The section has its own skin (assets/css/golf.css), copied from the look of Arccos's
web dashboard at Jack's request: black canvas, dark cards, green gained / red lost.
Pages are generated whole. Run from the repo root: python3 scripts/build_golf.py
"""
import json
import math
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAR_HOLES = {'3': 4, '4': 10, '5': 4}  # a typical 18-hole card

PAGES = [('golf.html', 'Overview'), ('golf-story.html', 'My game'), ('golf-driving.html', 'Driving'), ('golf-approach.html', 'Approach'),
         ('golf-short-game.html', 'Short game'), ('golf-putting.html', 'Putting'),
         ('golf-rounds.html', 'Rounds'), ('golf-trackman.html', 'TrackMan')]
CATS = [('driving', 'Driving', 'golf-driving.html'), ('approach', 'Approach', 'golf-approach.html'),
        ('short', 'Short', 'golf-short-game.html'), ('putting', 'Putting', 'golf-putting.html')]
BAND_COLORS = {'eagle': 'var(--accent-2)', 'birdie': 'var(--accent)', 'par': 'var(--mark)',
               'bogey': 'var(--signal-fill)', 'double+': 'var(--signal)'}


def num(v):
    return -float(v[1:]) if str(v).startswith('+') else float(v)


def show(v):
    return f'+{abs(v):.1f}' if v < 0 else f'{v:.1f}'


def month(d):
    return date.fromisoformat(d).strftime('%b %Y')


def decisive(rng):
    return bool(rng) and (rng[0] < 0) == (rng[1] < 0)


def rng_text(ci):
    if not ci:
        return ''
    fmt = lambda x: ('−' if x < 0 else '+') + f'{abs(x):.1f}'
    return f'{fmt(ci[0])} to {fmt(ci[1])}'


def sg(v, dec=1):
    cls = 'pos' if v > 0 else 'neg' if v < 0 else ''
    txt = ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.{dec}f}'
    return f'<span class="{cls}">{txt}</span>' if cls else txt


def chart(revs, today):
    x0, x1, y0, y1 = 44, 704, 24, 276
    pts = [(date.fromisoformat(r['date']), num(r['index'])) for r in revs]
    start, end = pts[0][0], date.fromisoformat(today)
    span = max((end - start).days, 1)
    top = math.ceil(max(v for _, v in pts) / 2) * 2
    X = lambda d: x0 + (d - start).days / span * (x1 - x0)
    Y = lambda v: y1 - v / top * (y1 - y0)
    out = []
    for g in range(0, top + 1, 2):
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                   f'<text x="{x0 - 8}" y="{Y(g) + 4:.1f}" class="yl">{g}</text>')
    out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" class="inv" stroke-dasharray="6 5"/>'
               f'<text x="{x1}" y="{Y(0) - 8:.1f}" class="ml" text-anchor="end">Scratch</text>')
    m = date(start.year, start.month, 1)
    while m <= end:
        if m >= start:
            out.append(f'<text x="{X(m):.1f}" y="300" class="xl">{m.strftime("%b")}</text>')
        m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    path, prev = [], None
    for d, v in pts:
        path.append(f'{"M" if prev is None else "L"}{X(d):.1f},{Y(prev if prev is not None else v):.1f}')
        path.append(f'L{X(d):.1f},{Y(v):.1f}')
        prev = v
    path.append(f'L{X(end):.1f},{Y(prev):.1f}')
    out.append(f'<path d="{" ".join(path)}" class="val"/>')
    low_d, low_v = min(pts, key=lambda p: (p[1], -p[0].toordinal()))
    out.append(f'<circle cx="{X(low_d):.1f}" cy="{Y(low_v):.1f}" r="4" class="dot"/>'
               f'<text x="{X(low_d):.1f}" y="{Y(low_v) + 20:.1f}" class="ml" text-anchor="middle">Low: {show(low_v)}</text>')
    out.append(f'<circle cx="{X(end):.1f}" cy="{Y(prev):.1f}" r="4" class="dot"/>'
               f'<text x="{X(end) - 6:.1f}" y="{Y(prev) - 12:.1f}" class="ml" text-anchor="end">Now: {show(prev)}</text>')
    return ('<div class="dca-scroll"><svg viewBox="0 0 720 312" role="img" class="dca-chart" '
            f'aria-label="Handicap Index from {month(revs[0]["date"])} to {month(today)}">\n' + '\n'.join(out) + '\n</svg></div>\n')


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------

SHELL = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="https://jackraney.com/{slug}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Jack Raney">
  <meta property="og:title" content="{ogtitle}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="https://jackraney.com/{slug}">
  <meta property="og:image" content="https://jackraney.com/assets/img/og.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="theme-color" content="#f4f1e8">
  <link rel="icon" href="assets/img/favicon-32.png" sizes="32x32" type="image/png">
  <link rel="icon" href="assets/img/favicon-64.png" sizes="64x64" type="image/png">
  <link rel="apple-touch-icon" href="assets/img/apple-touch-icon.png">
  <script>try{{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Besley:wght@400..700&family=Overpass:ital,wght@0,300..900;1,300..900&family=Overpass+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="assets/css/site.css">
  <link rel="stylesheet" href="assets/css/golf.css">
</head>
<body>

<a class="skip" href="#main">Skip to content</a>

<header class="gtop">
  <div class="who">
    <a class="wordmark" href="index.html">Jack Raney</a>
    <span class="chip">Index<b>{index}</b></span>
  </div>
  <nav class="gnav" aria-label="Golf section">{nav}</nav>
  <div class="gpills"><span class="gpill">Goal: Scratch</span><span class="gpill">{rounds_pill}</span>
    <button class="theme-toggle" type="button" aria-label="Switch theme">
      <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="7.25" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10 2.75a7.25 7.25 0 0 1 0 14.5z" fill="currentColor"/></svg>
    </button>
  </div>
</header>

<main id="main" class="gwrap">
{content}
<p class="gnote">{note}</p>
</main>
<script src="assets/js/site.js"></script>
</body>
</html>
'''


def nav_links(current):
    return ''.join(f'<strong>{t}</strong>' if p == current else f'<a href="{p}">{t}</a>' for p, t in PAGES)


EXPLAIN = {
    'index': ('What a Handicap Index is',
              'Not an average. Each round becomes a <b>differential</b>, which is the score adjusted '
              'for how hard that course plays. The index is the average of the best 8 of the last 20 '
              'differentials, so it describes my better days, not my typical ones. That is why my index '
              'is lower than my scoring average, and why both are true at once.'),
    'differential': ('Differential',
                     'One round\u2019s score, adjusted for course difficulty, so a 79 on a hard course can '
                     'beat a 76 on an easy one. A differential at or under my index means that round beat '
                     'my handicap.'),
    'scratch': ('Who "scratch" is here',
                'A 0.0 handicap player. Every comparison on these pages is against what that player would '
                'be expected to do from the same place on the course, not against tour professionals.'),
    'expected': ('Expected strokes, the idea everything else is built on',
                 'From any spot on a course there is an average number of strokes it takes to hole out. '
                 'From 150 yards in the fairway a scratch player averages about 2.9. From 15 feet, about '
                 '1.8. Those averages are the measuring stick: every shot moves me from one expected '
                 'number to another.'),
    'sg': ('Strokes gained, in one sentence',
           'Take the expected strokes where the ball started, subtract the expected strokes where it ended, '
           'subtract 1 for the shot I just played. Positive means I gained ground on scratch; negative means '
           'I lost it. A 150 yard approach to 15 feet is 2.9 &minus; 1.8 &minus; 1 = <b>+0.1</b>: slightly '
           'better than par for that shot.'),
    'categories': ('Why the four categories add up to the total',
                   'Every shot belongs to exactly one category, decided by where it was played from: off '
                   'the tee on a par 4 or 5 is driving, a full shot to the green is approach, anything '
                   'inside 50 yards that is not a putt is short game, and a putt is putting. Add the four '
                   'up and you get the whole gap to scratch, which is why they always sum to the total.'),
    'range': ('Why every number has a range',
              'These come from a handful of rounds, so each figure is an estimate. The range is the band the '
              'true number is 95% likely to sit in. When the range crosses zero, I genuinely cannot tell '
              'that part of my game apart from scratch yet, no matter what the headline number says. Those '
              'get called "not callable", and they never set the practice agenda.'),
    'thin': ('"Too few to read"',
             'A distance bucket with fewer than 8 shots behind it is greyed out and never chosen as a '
             'focus area. Three good chips in a row is not evidence. Under 3 shots it is not published '
             'at all.'),
    'gir': ('Green in regulation',
            'On the green in two shots fewer than par: one shot on a par 3, two on a par 4, three on a '
            'par 5. Miss it and I need an up and down to save par.'),
    'updown': ('Up and down',
               'Missed the green, then holed out in two more shots: one chip or pitch, one putt. The rate '
               'here counts only shots from inside 30 yards, which is what a scratch comparison is built '
               'on. The 30 to 50 yard pitches are reported separately, because mixing them in flatters '
               'the number.'),
    'prox': ('Proximity',
             'How far from the hole an approach finishes, measured as the middle value rather than the '
             'average so one shank does not move it. Closer means shorter putts, which is most of what '
             'putting is.'),
    'dispersion': ('Dispersion and miss tendency',
                   'Lateral is left and right spread, depth is long and short. Both are standard '
                   'deviations in yards: roughly two thirds of shots land inside that figure. The '
                   'tendency is where the middle of the pattern sits, which says more about club '
                   'selection and aim than any single miss.'),
    'threeputt': ('Three-putts',
                  'Three or more putts on one hole. What matters is what preceded them: the length of '
                  'the first putt. The data records where each putt started but not how far the second '
                  'one was left, so I can say long first putts come before three-putts, and not whether '
                  'the lag or the short one was the miss.'),
    'leak': ('What a "leak" is, and what the share means',
             'A bucket of shots that is measurably costing strokes against scratch, priced per round. '
             'The share is how much of the total available improvement sits in that one bucket, so a '
             '41% share means fixing it is worth 41% of everything on the table.'),
    'adjusted': ('Raw score and adjusted score',
                 'GHIN caps every hole at net double bogey before it works out a handicap, so a blow-up '
                 'hole counts for less than it cost me. The scorecard shows the <b>raw</b> score, what I '
                 'actually made. The round total beside the course name is the adjusted one GHIN posted, '
                 'which is why the two can differ.'),
    'makerate': ('Make rate against scratch',
                 'The share of putts holed from each distance band, next to what a scratch player holes '
                 'from the same band. Inside 3 feet everyone makes nearly all of them, so the bands that '
                 'matter are the ones between 5 and 20 feet, where the gap is real and the sample is '
                 'small.'),
    'carry': ('Carry, and why it is not the number on the sign',
              'Carry is where the ball lands, not where it finishes. On the course it rolls out, '
              'sometimes a long way, so a 150 yard carry is not a 150 yard club on firm ground. The '
              'gapping table below uses carry because it is the part a swing controls.'),
    'smash': ('Ball speed, club speed and smash factor',
              'Club speed is how fast the head is moving, ball speed is how fast the ball leaves, and '
              'smash factor is one divided by the other. It is a strike-quality number: about 1.50 off '
              'a driver is the ceiling, and anything well under it means the ball is not being found '
              'in the middle.'),
    'spread': ('Spread, and why it is not the average',
               'The middle 80% of shots with a club, halved. A 12 yard spread means a typical shot '
               'lands within 12 yards either side of the usual one. It ignores the two or three worst '
               'strikes of a session on purpose, because one cold top says nothing about a gap.'),
    'gapping': ('Gapping',
                'The carry distance between one club and the next. Even gaps mean every yardage has a '
                'club; a 25 yard hole between two of them is a shot that has to be hit soft or hard, '
                'which is where approach misses come from. A gap that is too small means a club is '
                'doing nothing.'),
    'corridor': ('The corridor',
                 'A 36 yard wide strip, 18 either side of the target line, which is roughly a generous '
                 'fairway. The driver figure is the share of balls that finished inside it, which is '
                 'the practice version of the penalty problem on the course.'),
    'swinglen': ('Why swing lengths are "inferred"',
                 'TrackMan records the ball, not the backswing. The wedge matrix groups each club\u2019s '
                 'shots by carry and calls the groups short, stock and full, which is a guess from the '
                 'result. It only appears for a club with enough shots and clear separation between '
                 'them, and it is never presented as something measured.'),
    'practicegrade': ('How a session is graded',
                      'Against the plan it was given, not against a perfect session. Only two things '
                      'are graded: whether the driver stayed in the corridor and whether the wedges '
                      'carried consistent distances. Carry accuracy against a target is not graded at '
                      'all, because the export records no intended target.'),
    'preview': ('Why these numbers are grey',
                'They are a worked example, not my practice. The page swaps to real figures the first '
                'time a TrackMan session is exported and emailed in, and the preview chip disappears '
                'with them.'),
    'plans': ('How practice follows from this',
              'The leak table is read straight into my practice sessions: the top leaks become the blocks '
              'I hit, and the session is built around them rather than around whatever I feel like '
              'practising. That is also why a bucket with too few shots is never allowed to rank, '
              'because a fluke would set the agenda for weeks.'),
    'penalty': ('What a penalty shot costs',
                'Measured, not assumed: tee shots that took a penalty are compared against my clean tee '
                'shots on the same holes. The difference is what one costs.'),
}


def ex(key):
    """One optional explanation, closed. The summary is kept short enough to read as a
    button; the full title and the explanation are inside."""
    title, body = EXPLAIN[key]
    label = title.split(',')[0]
    return (f'<details class="ex"><summary>{label}</summary>'
            f'<div><b>{title}.</b> {body}</div></details>')


def an(score):
    """"an 84", "a 79": the eighties are the only scores that take "an"."""
    return ('an ' if 80 <= score < 90 else 'a ') + f'{score:.0f}'


def explainers(*keys):
    """The same dropdowns the story page uses, put at the foot of the page whose numbers
    they explain. Closed by default, so the page reads exactly as it did without them."""
    body = '\n'.join('    ' + ex(k) for k in keys)
    return card('What these numbers mean', body)


def card(section, inner, cls='', icon='', explain=()):
    head = f'  <h2 class="gsect">{section}</h2>\n' if section else ''
    notes = ''.join('\n    ' + ex(k) for k in explain)
    if notes:
        notes = f'\n    <div class="ex-row">{notes}\n    </div>'
    return f'<section>\n{head}  <div class="gcard {cls}">\n{inner}{notes}\n  </div>\n</section>\n'


def statpair(a_lbl, a_val, b_lbl, b_val):
    return (f'<div class="statpair"><div><span class="lbl">{a_lbl}</span><span class="num num--lg">{a_val}</span></div>'
            f'<div><span class="lbl">{b_lbl}</span><span class="num num--lg">{b_val}</span></div></div>')


def rbar(frac, cls='', tick=None):
    t = f'<span class="tick" style="left:{tick:.0f}%"></span>' if tick is not None else ''
    return f'<span class="rbar"><i class="{cls}" style="width:{max(3, min(frac, 1) * 100):.0f}%"></i>{t}</span>'


# ---------------------------------------------------------------------------
# hub cards
# ---------------------------------------------------------------------------

# Scratch benchmarks used for the plain-English comparisons. Sources on the pages that
# use them: Shot Scope by-handicap data (GIR, up-and-down) and Arccos (putting).
SCRATCH = {'gir_pct': 52, 'updown_pct': 54, 'putts': 29.9, 'three_putts': 0.8}


def briefing(stats, g):
    """The whole game in one short card: the gap, one line on what is established, the four
    numbers behind it, the three jobs. Every value is read off the data, so it cannot go stale."""
    sg, leaks = stats['sg'], (stats.get('leaks') or [])
    if not leaks:
        return card('The short version',
                    '    <p style="margin:0;font-size:0.95rem">Not enough tracked rounds yet to say where '
                    'the strokes go. Play a few with the sensors on and this fills in.</p>')
    gap = abs(sg['total'])
    idx = g['revisions'][-1]['index']
    r18 = [r for r in (g.get('recent_rounds') or []) if r.get('holes') == 18 and r.get('score')]
    avg = sum(r['score'] for r in r18) / len(r18) if r18 else None

    d, a, sh, p = stats['driving'], stats['approach'], stats['short'], stats['putting']
    rounds18 = stats['holes'] / 18
    gs = sh.get('updown_greenside') or sh['updown']
    pitch = sh.get('updown_pitch') or {}

    ci = sg.get('ci') or {}
    names = {'driving': 'driving', 'approach': 'approach play', 'short': 'the short game', 'putting': 'putting'}
    real = [names[c] for c in ('driving', 'approach', 'short', 'putting') if decisive(ci.get(c))]
    unsure = [names[c] for c in ('driving', 'approach', 'short', 'putting') if not decisive(ci.get(c))]
    join = lambda xs: xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]
    if real:
        verdict = (f'{join(real).capitalize()} {"is" if len(real) == 1 else "are"} measurably worse than scratch'
                   + (f'. {join(unsure).capitalize()} {"is" if len(unsure) == 1 else "are"} not callable yet'
                      if unsure else '') + '.')
    else:
        verdict = f'Nothing clears the bar yet: over {stats["holes"]} holes every range still includes zero.'

    rows = [('Tee penalties', f'{d["tee_penalties"]} in {d["tee_shots"]} tee shots \u00b7 driver median '
             f'{d["driver_median_yd"]} yd, so it is direction, not distance',
             f'{d["tee_penalties"] / rounds18:.1f}<small>/rnd</small>')]
    if gs.get('of'):
        basis = f'{gs["made"]} of {gs["of"]} \u00b7 scratch about {SCRATCH["updown_pct"]}%'
        if pitch.get('of'):
            basis += f' \u00b7 {pitch["made"]} of {pitch["of"]} from 30 to 50 yd'
        rows.append(('Up and down, inside 30 yd', basis, f'{round(gs["made"] / gs["of"] * 100)}%'))
    if p['three_putts']:
        rows.append(('Three-putts', f'first putts {p["three_putt_first_ft"]} ft, against '
                     f'{p["two_putt_first_ft"]} ft on holes you two-putted', p['three_putts']))
    rows.append(('Greens in regulation', f'scratch about {SCRATCH["gir_pct"]}%', f'{a["gir_pct"]}%'))

    facts = ''.join(f'<li><span class="k">{k}<small>{n}</small></span><span class="val">{v}</span></li>'
                    for k, n, v in rows)
    ranks = ''.join(f'<li><span class="r">{i}</span><span class="k">{l["name"]}</span>'
                    f'<span class="val">{abs(l["per_round"]):.1f}</span></li>'
                    for i, l in enumerate(leaks[:3], 1))

    head = (f'    <div class="hero-score"><span class="num num--xl">{gap:.1f}</span>'
            f'<span class="vs">strokes from scratch, per 18 holes</span></div>\n'
            f'    <p class="goal-line">Index {idx}'
            + (f' \u00b7 scoring average {avg:.1f}' if avg else '') +
            f' \u00b7 {stats["rounds_n"]} tracked rounds, {stats["holes"]} holes</p>\n'
            f'    <p class="brief-verdict">{verdict}</p>\n')
    body = f'    <ul class="brows">{facts}</ul>\n'
    todo = ('    <p class="lbl" style="margin-top:1.2rem">What to work on \u00b7 strokes a round</p>\n'
            f'    <ol class="ranks">{ranks}</ol>\n')
    note = ('    <p class="vs-note" style="text-align:left">Read off the tracked rounds daily. '
            'The practice plans follow these three lines.</p>')
    return card('The short version', head + body + todo + note, cls='gcard--hero')


def hero_card(stats, g):
    recent = [r for r in (g.get('recent_rounds') or []) if r.get('score')]
    full18 = [r for r in recent if r.get('holes') == 18]
    idx = num(g['revisions'][-1]['index'])
    tracked_dates = {r['date'] for r in stats['rounds']} if stats else set()
    rows = []
    for r in recent[:5]:
        d = date.fromisoformat(r['date']).strftime('%b %-d')
        name = r.get('course') or 'Posted round'
        sub = f'{d} \u00b7 {r["holes"]} holes' + (' \u00b7 shots tracked' if r['date'] in tracked_dates else '')
        diff = r.get('differential')
        dcls = 'pos' if diff is not None and diff <= idx else 'warn'
        dtxt = f'<span class="num num--md {dcls}">{diff:.1f}</span>' if diff is not None else ''
        rows.append(f'<li><span class="course"><b>{name}</b><small>{sub}</small></span>'
                    f'<span class="score"><span class="num num--md">{r["score"]}</span>{dtxt}</span></li>')
    avg = sum(r['score'] for r in full18) / max(1, len(full18))
    gap = (f'On the {stats["rounds_n"]} rounds with shot data, which averaged '
           f'{stats["scoring"]["avg18"]:.1f}, I was {abs(stats["sg"]["total"]):.0f} strokes a round from scratch.'
           ) if stats else f'Scratch is 0.0. My index is {show(idx)}.'
    inner = (f'    <div class="hero-score"><span class="num num--xl">{avg:.1f}</span>'
             f'<span class="vs">avg of my last {len(full18)} posted rounds</span></div>\n'
             f'    <p class="goal-line">{gap}</p>\n'
             f'    <p class="lbl" style="margin-top:1.2rem">Recent rounds \u00b7 score and differential</p>\n'
             f'    <ul class="rounds-list">{"".join(rows)}</ul>\n'
             f'    <p class="vs-note" style="text-align:left">From my GHIN record, every posted round. A differential at or '
             f'under my index beat my handicap.</p>')
    return card('Scoring', inner, cls='gcard--hero', explain=('index', 'differential'))


def scoring_card(stats):
    b = stats['scoring']['bands']
    total = sum(b.values()) or 1
    segs = ''.join(f'<i style="width:{v / total * 100:.1f}%;background:{BAND_COLORS[k]}"></i>' for k, v in b.items())
    cells = ''.join(f'<div><span class="num num--lg">{v}</span>'
                    f'<span class="blbl" style="color:{BAND_COLORS[k]}">{k.replace("+", "+").replace("double+", "dbl+").title()}</span>'
                    f'<small>{v / total:.0%}</small></div>' for k, v in b.items())
    inner = (statpair('Rounds', stats['rounds_n'], 'Holes', stats['holes'])
             + f'\n    <div class="bandbar">{segs}</div>\n    <div class="bands">{cells}</div>'
             + '\n    <p class="vs-note">Sensor-tracked rounds only</p>')
    return card('Scoring bands', inner)


def sg_card(stats):
    per, worst = stats['sg']['per_round'], stats['sg']['focus']
    tiles = []
    for key, name, href in CATS:
        v = per[key]
        color = 'var(--gain)' if v > 0 else 'var(--lose-hard)' if key == worst else 'var(--lose)'
        chip = '<span class="focus-chip">Focus</span>' if key == worst else ''
        ci = (stats['sg'].get('ci') or {}).get(key)
        band = f'<span class="tile-ci">{rng_text(ci)}</span>' if ci else ''
        tiles.append(f'<a class="sg-tile{" focus" if key == worst else ""}" href="{href}">{chip}'
                     f'<span class="lbl">{name}</span><span class="tbar"><i style="width:{min(abs(v) / 5, 1) * 100:.0f}%;background:{color}"></i></span>'
                     f'<span class="num num--md">{sg(v)}</span>{band}</a>')
    worst_name = dict((k, n) for k, n, _ in CATS)[worst]
    inner = (f'    <div class="sg-total"><div><span class="lbl">Total SG</span><p>Per round vs scratch</p></div>'
             f'<span class="num num--lg">{sg(stats["sg"]["total"])}</span></div>\n'
             f'    <div class="sg-tiles">{"".join(tiles)}</div>\n'
             f'    <p class="sg-line"><b>{worst_name}</b> is my biggest opportunity.</p>')
    return card('Strokes gained breakdown', inner, explain=('sg', 'range'))


def leaks_card(stats):
    rows = []
    for i, l in enumerate(stats['leaks'], 1):
        rows.append(f'<li><span class="leak__rank">{i}</span><div><p class="leak__name">{l["name"]}</p>'
                    f'<p class="leak__gain">Fixing this is worth about {abs(l["per_round"]):.1f} strokes a round.</p>'
                    + rbar(l['share'] / 100)
                    + f'<p class="leak__basis">{l["share"]}% of the focus-area upside · {l["basis"]}</p></div></li>')
    return card('Where to focus', f'    <ol class="leaks">{"".join(rows)}</ol>',
                explain=('leak', 'thin'))


def handicap_card(g):
    revs, today = g['revisions'], g['updated']
    cur = num(revs[-1]['index'])
    year_ago = date.fromisoformat(today).replace(year=date.fromisoformat(today).year - 1).isoformat()
    low = min(num(r['index']) for r in revs if r['date'] >= year_ago)
    best = g.get('best_differential')
    minus = '−'
    best_txt = (f'{minus if best < 0 else ""}{abs(best):.1f}') if best is not None else '–'
    chips = (f'<div class="statpair" style="grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:1rem">'
             f'<div><span class="lbl">Handicap Index</span><span class="num num--lg">{show(cur)}</span></div>'
             f'<div><span class="lbl">Low, 12 months</span><span class="num num--lg">{show(low)}</span></div>'
             f'<div><span class="lbl">Rounds, 12 months</span><span class="num num--lg">{g["rounds_last_12_months"]}</span></div>'
             f'<div><span class="lbl">Best differential</span><span class="num num--lg">{best_txt}</span></div></div>')
    return card('Handicap Index, every revision', chips + chart(revs, today))


def bypar_card(g):
    par = g.get('by_par') or {}
    if not par:
        return ''
    rows, per_round = [], {}
    for p in ('3', '4', '5'):
        if p in par:
            per_round[p] = par[p]['avg_over_par'] * PAR_HOLES[p]
            rows.append(f'<li><span class="from">Par {p}s</span>'
                        + rbar(per_round[p] / 10)
                        + f'<span class="n">{par[p]["holes"]} holes</span>'
                        f'<span class="val neg">+{per_round[p]:.1f}</span></li>')
    worst = max(per_round, key=per_round.get)
    lead = f'Par {worst}s cost me the most, about {per_round[worst]:.0f} strokes over par on a typical card. Per round, from my whole GHIN record:'
    return card('Where the strokes go', f'    <p style="margin:0 0 0.8rem;font-size:0.92rem">{lead}</p>\n    <ul class="drows">{"".join(rows)}</ul>')


def highlights_card(stats):
    d = stats['driving']
    items = [('Driver, longest', f'{d["driver_longest_yd"]} yd'), ('Driver, median', f'{d["driver_median_yd"]} yd'),
             ('Greens in regulation', f'{stats["approach"]["gir_pct"]}%'), ('Putts per round', stats['putting']['putts_round'])]
    rows = ''.join(f'<li><span class="course"><b>{n}</b></span><span class="score"><span class="num num--md">{v}</span></span></li>'
                   for n, v in items)
    return card('Highlights', f'    <ul class="rounds-list" style="margin-top:0">{rows}</ul>')


# ---------------------------------------------------------------------------
# facet pages
# ---------------------------------------------------------------------------

def focus_card(title, text, big_val, big_lbl):
    return card('', (f'    <div class="focus-card"><div><h2>Focus area: {title}</h2><p>{text}</p></div>'
                     f'<div class="big"><span class="num num--lg">{big_val}</span><small>{big_lbl}</small></div></div>'))


def drow(frm, bar, n, val, thin=False):
    cls = ' class="thin"' if thin else ''
    note = ' · too few to read' if thin else ''
    return (f'<li{cls}><span class="from">{frm}</span>{bar}<span class="n">{n}{note}</span>'
            f'<span class="val">{val}</span></li>')


def page_driving(stats, g):
    d = stats['driving']
    fw = d['fairways']
    pen_leak = next((l for l in stats.get('leaks', []) if 'penalt' in l['name'].lower()), None)
    leaks_ = stats.get('leaks') or []
    first = bool(leaks_) and leaks_[0] is pen_leak
    focus_line = (f'Penalty balls off the tee cost about {abs(pen_leak["per_round"]):.1f} strokes a round'
                  + (', the largest single thing in my game right now.' if first else
                     f', ranked {leaks_.index(pen_leak) + 1} of the things worth fixing.') if pen_leak else
                  'Penalties off the tee are no longer clearing the bar as a measured leak. '
                  'Distance and dispersion are what is left here.')
    left = (focus_card('off the tee', focus_line, sg(d['sg_round']), 'Strokes/rnd')
            + card('', statpair('Driver, median', f'{d["driver_median_yd"]} yd', 'Longest', f'{d["driver_longest_yd"]} yd'))
            + card('', statpair('Tee-shot penalties', d['tee_penalties'], 'Fairways', f'{fw["hit"] / fw["of"]:.0%}'),
                   explain=('penalty', 'sg')))
    driver_pct = d['driver_shots'] / d['tee_shots'] if d['tee_shots'] else 0
    td = d.get('tee_decision') or {}
    tee_card = ''
    if td.get('clubs'):
        rows = []
        for c in td['clubs']:
            med = c['median_yd'] or '–'
            rows.append(f'<tr><td>{c["club"]}</td><td>{c["shots"]}</td><td>{sg(c["sg_per_shot"], 2)}</td>'
                        f'<td>{c["penalty_rate"]}%</td><td>{med}</td></tr>')
        rows = ''.join(rows)
        v = td.get('verdict') or {}
        if v and v.get('callable'):
            verdict = (f'<b>{v["better"]} is the better play.</b> It returns {abs(v["gap_per_shot"]):.2f} strokes '
                       f'more per tee shot than {v["worse"].lower()}, and the ranges do not overlap.')
        elif v:
            verdict = (f'<b>Not callable yet.</b> {v["better"]} is ahead by {abs(v["gap_per_shot"]):.2f} strokes a '
                       f'tee shot and goes {abs(v["yards"])} yd further, but the ranges still overlap, so I cannot '
                       f'say the trade is paying. More tracked rounds decide it.')
        else:
            verdict = 'Not enough tee shots yet to compare clubs.'
        tee_card = card('Is the lay-up paying?',
                        '    <div class="table-wrap"><table class="gtable"><thead><tr><th>Club</th><th>Tee shots</th>'
                        '<th>SG per shot</th><th>Penalty rate</th><th>Median</th></tr></thead><tbody>'
                        + rows + '</tbody></table></div>\n'
                        f'    <p style="margin:0.8rem 0 0;font-size:0.92rem">{verdict}</p>')
    right = (tee_card + card('Club off the tee',
                  f'    <p style="margin:0;font-size:0.95rem">Driver on {d["driver_shots"]} of {d["tee_shots"]} tee shots '
                  f'({driver_pct:.0%}); the rest were 3-wood or an iron. The distance numbers above are driver only, '
                  f'measured from shot GPS across {d["driver_measured"]} drives that did not take a penalty. '
                  f'Blending every club off the tee into one "average drive" reads nearly 40 yd shorter '
                  f'and means nothing, so it is not on this page.</p>')
             + card('What matters off the tee',
                 f'    <p style="margin:0;font-size:0.95rem">I hit {fw["hit"]} of {fw["of"]} fairways ({fw["hit"] / fw["of"]:.0%}). '
                 'That number barely matters: in Shot Scope’s data, fairway percentage is almost flat from scratch to a '
                 '20 handicap. What separates handicaps off the tee is the disaster rate, penalty balls and the spots you '
                 + (f'The penalties alone cost about {abs(pen_leak["per_round"]):.1f} strokes a round.'
                    if pen_leak else 'Penalties are not clearing the bar as a measured leak right now.')
                 + '</p>'))
    return (f'<div class="ggrid"><div class="gcol">{left}</div><div class="gcol">{right}</div></div>')


def page_approach(stats, g):
    a = stats['approach']
    rows = ''.join(drow(f'{b}', rbar(abs(v['sg_round']) / 2.5, 'ok' if v['sg_round'] > 0 else ''),
                        f'{v["shots"]} shots', sg(v['sg_round']), v.get('thin')) for b, v in a['buckets'].items())
    m, disp = a['miss_dir'], a.get('dispersion') or {}
    missgrid = (f'    <div class="miss-grid">'
                f'<span class="miss miss--long">Long<b>{m["long"]}</b></span>'
                f'<span class="miss miss--left">Left<b>{m["left"]}</b></span>'
                f'<span class="miss miss--gir">On green<b>{a["gir_pct"]}%</b></span>'
                f'<span class="miss miss--right">Right<b>{m["right"]}</b></span>'
                f'<span class="miss miss--short">Short<b>{m["short"]}</b></span></div>\n'
                f'    <p class="vs-note" style="text-align:center">Typical spread ±{disp.get("lateral_sd", "?")} yd across, '
                f'±{disp.get("depth_sd", "?")} yd deep · usual miss: {disp.get("tendency", "?")}</p>')
    left = (focus_card('Approach', 'I’m losing strokes on approach, spread across the distances rather than one band.',
                       sg(a['sg_round']), 'Strokes/rnd')
            + card('', statpair('Greens in regulation', f'{a["gir_pct"]}%', 'Shots', sum(v['shots'] for v in a['buckets'].values())))
            + card('', statpair('Proximity, greens hit', f'{a["prox_gir_ft"]} ft', 'Proximity, all', f'{a["prox_all_ft"]} ft')))
    mid = card('SG by distance (yd)', f'    <ul class="drows">{rows}</ul>')
    right = card('Where approach shots finish', missgrid, explain=('gir', 'prox', 'dispersion'))
    return (f'<div class="ggrid3"><div class="gcol">{left}</div><div class="gcol">{mid}</div><div class="gcol">{right}</div></div>')


def page_short(stats, g):
    s = stats['short']
    ud = s.get('updown_greenside') or s['updown']
    pitch = s.get('updown_pitch') or {}
    disp = s.get('dispersion') or {}
    rows = ''.join(drow(f'{b}', rbar(abs(v['sg_round']) / 2.5, 'ok' if v['sg_round'] > 0 else ''),
                        f'{v["shots"]} shots', sg(v['sg_round']), v.get('thin')) for b, v in s['buckets'].items())
    ud_pct = (ud['made'] / ud['of']) if ud.get('of') else 0
    focus_line = (f'A scratch player gets up and down a little over half the time from inside 30 yards. '
                  f'I’m at {ud_pct:.0%} ({ud["made"]} of {ud["of"]})'
                  + (f', and {pitch["made"]} of {pitch["of"]} from 30 to 50.' if pitch.get('of') else '.'))
    left = (focus_card('inside 50 yards', focus_line, sg(s['sg_round']), 'Strokes/rnd')
            + card('', statpair('Up and down, inside 30 yd',
                                f'{(s.get("updown_greenside") or ud)["made"]}/{(s.get("updown_greenside") or ud)["of"]}',
                                'Usual miss', (disp.get('tendency') or '?').title())))
    right = card('SG by distance (yd)', f'    <ul class="drows">{rows}</ul>', explain=('updown', 'thin'))
    return (f'<div class="ggrid"><div class="gcol">{left}</div><div class="gcol">{right}</div></div>')


def page_putting(stats, g):
    p = stats['putting']
    solid = {b: v for b, v in p['buckets'].items() if not v.get('thin')} or p['buckets']
    worst = min(solid, key=lambda b: solid[b]['sg_round'])
    sg_rows = ''.join(drow(f"{b}'", rbar(abs(v['sg_round']) / 1.5, 'ok' if v['sg_round'] > 0 else ''),
                           f'{v["n"]} putts', sg(v['sg_round']), v.get('thin')) for b, v in p['buckets'].items())
    make_rows = []
    for b, v in p['buckets'].items():
        delta = v['made_pct'] - (v['scratch_pct'] or 0)
        cls = 'pos' if delta > 0 else 'neg'
        make_rows.append(drow(f"{b}'", rbar(v['made_pct'] / 100, 'ok' if delta >= 0 else '', tick=v['scratch_pct']),
                              f'{v["n"]} putts', f'<span class="{cls}">{v["made_pct"]}% ({delta:+d}%)</span>',
                              v.get('thin')))
    autopsy = card('Three-putts',
                   f'    <p style="margin:0 0 0.5rem;font-size:0.95rem">{p["three_putts"]} three-putt holes. '
                   f'On them my first putt averaged {p["three_putt_first_ft"]} ft, against '
                   f'{p["two_putt_first_ft"]} ft on holes I two-putted. Long first putts are what precedes '
                   f'them.</p>'
                   '    <p class="leak__basis">Arccos does not record where the second putt was played from, '
                   'so I cannot say whether these were poor lags or missed short ones. Only the first putt '
                   'is measured.</p>', explain=('threeputt',))
    left = (focus_card(f'{worst} ft putts', 'Tighten this band first; the rest of my putting holds up against scratch.',
                       sg(p['sg_round']), 'Strokes/rnd')
            + card('', statpair('Putts per round', p['putts_round'], '3-putts/rnd', round(p['three_putts'] / (stats['holes'] / 18), 1))))
    mid = (card('SG by putt distance', f'    <span class="opp-chip">#1 opportunity: {worst} ft</span>\n    <ul class="drows">{sg_rows}</ul>')
           + card('Make rate by distance', f'    <ul class="drows">{"".join(make_rows)}</ul>\n'
                  '    <p class="vs-note">▏ marks a scratch player’s make rate (Arccos data)</p>',
                  explain=('makerate', 'thin')))
    right = autopsy
    return (f'<div class="ggrid3"><div class="gcol">{left}</div><div class="gcol">{mid}</div><div class="gcol">{right}</div></div>')


def band_for(over):
    """The scoring band of one hole. 'dbl' rather than the bands card's 'double+'
    because this one becomes a CSS class."""
    return ('eagle' if over <= -2 else 'birdie' if over == -1 else 'par' if over == 0
            else 'bogey' if over == 1 else 'dbl')


def merge_card(ghin, sensor):
    """One hole-by-hole card from whichever sources exist.

    GHIN is the posted card and wins on par, score and putts; the sensors add strokes
    gained, and stand alone when GHIN holds no hole detail. A hole the sensors missed
    simply has no strokes-gained figure rather than a zero."""
    holes = {}
    for h in (ghin or []):
        holes[h['h']] = {'par': h['par'], 'score': h.get('raw') or h['adj'], 'putts': h.get('putts'),
                         'yds': h.get('yds'), 'sg': None}
    for h in (sensor or []):
        e = holes.get(h['h'])
        if e is None:
            e = holes[h['h']] = {'par': h['par'], 'score': h['score'], 'putts': h.get('putts'), 'sg': None}
        e['sg'] = h.get('sg')
        if e.get('yds') is None:
            e['yds'] = h.get('yds')
    return [dict(holes[k], h=k) for k in sorted(holes)]


def nine(label, rows, show_sg):
    """One half of a scorecard: holes across, yards / par / score / putts / SG down."""
    dash = chr(8211)
    cells = lambda key, fmt=str: ''.join(
        f'<td>{fmt(r[key]) if r.get(key) is not None else dash}</td>' for r in rows)
    tot = lambda key: sum(r[key] for r in rows if r.get(key) is not None)
    head = ''.join(f'<th>{r["h"]}</th>' for r in rows)
    out = [f'<tr class="r-hole"><th class="rl">{label}</th>{head}'
           f'<th class="tot">{"Out" if label == "Front" else "In"}</th></tr>']
    if any(r.get('yds') is not None for r in rows):
        out.append(f'<tr class="r-yds"><th class="rl">Yards</th>{cells("yds", lambda v: f"{v:,}")}'
                   f'<td class="tot">{tot("yds"):,}</td></tr>')
    out.append(f'<tr class="r-par"><th class="rl">Par</th>{cells("par")}'
               f'<td class="tot">{tot("par")}</td></tr>')
    score = ''.join(
        f'<td><span class="mk mk--{band_for(r["score"] - r["par"])}">{r["score"]}</span></td>'
        if r.get('score') is not None else f'<td>{dash}</td>' for r in rows)
    out.append(f'<tr class="r-score"><th class="rl">Score</th>{score}'
               f'<td class="tot">{tot("score")}</td></tr>')
    if any(r.get('putts') is not None for r in rows):
        out.append(f'<tr class="r-putts"><th class="rl">Putts</th>{cells("putts")}'
                   f'<td class="tot">{tot("putts")}</td></tr>')
    if show_sg:
        sgc = ''.join(f'<td>{sg(r["sg"]) if r.get("sg") is not None else dash}</td>' for r in rows)
        out.append(f'<tr class="r-sg"><th class="rl">SG</th>{sgc}'
                   f'<td class="tot">{sg(round(tot("sg"), 1))}</td></tr>')
    return f'    <div class="table-wrap"><table class="scard">{"".join(out)}</table></div>\n'


def tee_line(r, rows):
    """Which tees, how hard they rate, and the card's own totals. Each piece appears only
    when it exists: GHIN carries the tee and rating, the yardages come from the course card."""
    bits = []
    if r.get('tee'):
        bits.append(f'{r["tee"]} tees')
    if r.get('rating') and r.get('slope'):
        bits.append(f'{r["rating"]} / {r["slope"]}')
    elif r.get('slope'):
        bits.append(f'slope {r["slope"]}')
    yds = sum(h['yds'] for h in rows if h.get('yds') is not None)
    if yds:
        bits.append(f'{yds:,} yards')
    par = sum(h['par'] for h in rows)
    if par:
        bits.append(f'par {par}')
    line = ' \u00b7 '.join(bits)
    return f'    <p class="scard-tees">{line}</p>\n' if bits else ''


def scorecard(rows, source, holes):
    if not rows:
        return ''
    show_sg = any(r.get('sg') is not None for r in rows)
    front = [r for r in rows if r['h'] <= 9]
    back = [r for r in rows if r['h'] > 9]
    html = (nine('Front', front, show_sg) if front else '') + (nine('Back', back, show_sg) if back else '')
    total = sum(r['score'] for r in rows if r.get('score') is not None)
    putts = [r['putts'] for r in rows if r.get('putts') is not None]
    bits = [f'Round of {total}']
    if putts:
        bits.append(f'{sum(putts)} putts')
    if show_sg:
        bits.append(f'{sg(round(sum(r["sg"] for r in rows if r.get("sg") is not None), 1))} strokes gained')
    line = ' \u00b7 '.join(bits)
    short = (f' Only {len(rows)} of the {holes} holes have shot data, so this card is '
             'the part that was recorded.') if holes and len(rows) < holes else ''
    return html + f'    <p class="scard-note">{line}. {source}{short}</p>\n'


def page_rounds(stats, g):
    idx = num(g['revisions'][-1]['index'])
    sensor = {r['date']: r for r in stats['rounds']}
    items = []
    for r in (g.get('recent_rounds') or []):
        if not r.get('score'):
            continue
        d = date.fromisoformat(r['date']).strftime('%b %d, %Y')
        diff = r.get('differential')
        dcls = 'pos' if diff is not None and diff <= idx else 'warn'
        dtxt = f'<span class="df {dcls}">{diff:.1f}</span>' if diff is not None else '<span class="df">\u2013</span>'
        tracked = sensor.get(r['date'])
        name = r.get('course') or '\u2013'
        tag = '<small>shots tracked</small>' if tracked else ''
        # A row with nothing to open should say why rather than ignoring the click. `raw` is the
        # sum of GHIN's hole scores, so its absence is the one case where no card can ever exist.
        if not tracked and not r.get('card') and not r.get('raw'):
            tag = '<small class="muted-tag">posted as a total, no hole detail</small>'
        head = (f'<span class="c"><b>{name}</b><small>{d} \u00b7 {r["holes"]} holes</small>{tag}</span>'
                f'<span class="sc num num--md">{r["score"]}</span>{dtxt}')
        rows = merge_card(r.get('card'), (tracked or {}).get('card'))
        if not rows:
            items.append(f'<li class="rnd rnd--flat">{head}<span class="chev chev--none"></span></li>')
            continue
        source = ('Par and score from my GHIN card; strokes gained from the shot data.'
                  if r.get('card') and tracked else 'From my GHIN card, hole by hole.'
                  if r.get('card') else 'From the shot data, hole by hole.')
        items.append(f'<li><details class="rnd"><summary>{head}<span class="chev"></span></summary>'
                     f'<div class="scard-body">\n{tee_line(r, rows)}{scorecard(rows, source, r["holes"])}'
                     '    </div></details></li>')
    ghin_table = card('Latest posted rounds (GHIN)',
                      f'    <ul class="rnds">{"".join(items)}</ul>\n'
                      '    <p class="vs-note">Open a round for the scorecard. A differential at or under my '
                      'index beat my handicap. Rounds without sensor shots count for scoring and handicap, '
                      'but not for the strokes-gained pages.</p>',
                      explain=('adjusted', 'differential', 'index'))
    rows = []
    for r in stats['rounds']:
        tot = sum(r['sg'].values())
        d = date.fromisoformat(r['date']).strftime('%b %d, %Y')
        cells = ''.join(f'<td>{sg(r["sg"].get(k, 0))}</td>' for k, _, _ in CATS)
        rows.append(f'<tr><td>{d}</td><td>{r["course"]}</td><td class="num num--md">{r["score"]}{"" if r["holes"] == 18 else " (9)"}</td>'
                    f'<td>{sg(r["score"] - r["par"], 0)}</td>{cells}<td>{sg(tot)}</td></tr>')
    table = card('Every sensor-tracked round',
                 '    <div class="table-wrap"><table class="gtable"><thead><tr><th>Date</th><th>Course</th><th>Score</th>'
                 '<th>To par</th><th>Tee</th><th>App</th><th>Short</th><th>Putt</th><th>Total SG</th></tr></thead><tbody>'
                 + ''.join(rows) + '</tbody></table></div>')
    bypar = ''.join(drow(f'Par {p}s', rbar(abs(v) / 2), '', sg(-abs(v)) if v > 0 else sg(v))
                    for p, v in stats['scoring']['by_par'].items())
    bylen = ''.join(drow(b, rbar(abs(v) / 2), '', sg(-abs(v)) if v > 0 else sg(v))
                    for b, v in sorted(stats['scoring']['par4_by_length'].items()))
    small = (f'<div class="ggrid">{card("Average over par, by hole", f"    <ul class=_drows_>{bypar}</ul>".replace("_", chr(34)))}'
             f'{card("Par 4s by length (yd)", f"    <ul class=_drows_>{bylen}</ul>".replace("_", chr(34)))}</div>')
    return ghin_table + table + small


def trackman_data():
    """data/trackman.json, written by Archibald's trackman skill from TPS exports.
    Absent or empty until the first session lands, which is the normal state."""
    path = os.path.join(ROOT, 'data', 'trackman.json')
    if not os.path.exists(path):
        return None
    try:
        tm = json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return tm if tm.get('clubs') else None


def _loop_rows(tm, stats):
    """Pair each on-course leak with what the sim says about the club it needs.

    One row per leak, and only when there is a measurement on the practice side:
    a leak with nothing to pair against is left out rather than given a number.
    """
    clubs = {c['club']: c for c in tm['clubs']}
    wedge_spreads = [c['carry_spread'] for c in tm['clubs']
                     if c.get('carry_spread') and (c['club'] in ('Pw', 'Gw', 'Sw', 'Lw')
                                                   or c['club'].endswith('°'))]
    rows, shown = [], set()
    for leak in (stats.get('leaks') or [])[:3]:
        name = leak['name'].lower()
        measured = target = None
        kind = 'driver' if ('penalt' in name or 'driv' in name or 'tee' in name) else 'wedge'
        if kind in shown:
            continue          # one practice figure answers one leak, not three
        if kind == 'driver':
            d = clubs.get('Dr')
            if d and d.get('corridor_pct') is not None:
                measured = '%d%% of drives inside a 36 yd corridor · ±%s yd spread' % (
                    d['corridor_pct'], d.get('side_spread', '?'))
                target = 'two thirds inside the corridor'
                frac = d['corridor_pct'] / 100.0
        elif wedge_spreads:
            med = sorted(wedge_spreads)[len(wedge_spreads) // 2]
            measured = '±%s yd carry spread across the wedges' % med
            target = 'within ±4 yd'
            frac = max(0.05, min(1.0, 4.0 / med)) if med else 0.05
        if not measured:
            continue
        shown.add(kind)
        rows.append('<li><span class="leak__rank">%d</span><div>'
                    '<p class="leak__name">%s</p>'
                    '<p class="leak__gain">On the course: <b>%.1f strokes a round</b>. '
                    'Practice target: %s.</p>%s'
                    '<p class="leak__basis">Measured in the bay: %s</p></div></li>'
                    % (len(rows) + 1, leak['name'], abs(leak['per_round']), target,
                       rbar(frac), measured))
    if not rows:
        return ''
    return '    <ul class="leaks">%s</ul>' % ''.join(rows)


def grade_text(grade):
    """A session's grade against its plan. The skill publishes the whole grading dict, but the
    same field is a plain summary string elsewhere in that pipeline, so accept either."""
    if isinstance(grade, dict):
        return grade.get('summary') or '\u2014'
    return str(grade) if grade else '\u2014'


def page_trackman_real(tm, stats):
    """The TrackMan tab on real measurements."""
    clubs = [c for c in tm['clubs'] if c.get('carry')]
    longest = max([c['carry'] for c in clubs] or [1])
    gap_rows = ''.join(
        drow(c['club'], rbar(c['carry'] / longest, 'neu'),
             ('±%s yd' % c['carry_spread']) if c.get('carry_spread') else ('%s shots' % c.get('n', '?')),
             str(c['carry']), c.get('thin'))
        for c in clubs)

    withside = [c for c in tm['clubs'] if c.get('side_spread') is not None]
    widest = max([c['side_spread'] for c in withside] or [1]) or 1
    disp_rows = ''.join(
        drow(c['club'], rbar(c['side_spread'] / widest, '' if c['side_spread'] > 15 else 'ok'),
             'misses %s' % c.get('side_bias', '?'), '±%s' % c['side_spread'], c.get('thin'))
        for c in withside)

    wrows = ''.join(
        '<tr><td>%s</td><td>%s</td><td>%s</td><td class="num num--md">%s</td></tr>'
        % (w['club'], w.get('half', '—'), w.get('three_q', '—'), w.get('full', '—'))
        for w in tm['wedges'])
    inferred = any(w.get('inferred') for w in tm['wedges'])
    wedge = ('    <div class="table-wrap"><table class="gtable"><thead><tr><th>Club</th>'
             '<th>1/2</th><th>3/4</th><th>Full</th></tr></thead><tbody>%s</tbody></table></div>\n'
             '    <p class="vs-note">Carries in yards.%s</p>'
             % (wrows, ' Swing lengths inferred from carry clusters: the export records '
                       'no swing length, so this is a reading of the numbers.' if inferred else ''))

    sess_rows = ''.join(
        '<li><span class="course"><b>%s</b><small>%s · %d balls</small></span>'
        '<span class="score"><span class="n">%s</span></span></li>'
        % (s['label'], s['date'], s['balls'],
           grade_text(s.get('grade')))
        for s in tm['sessions'])

    u = tm.get('units') or {}
    note = ('Measured on TrackMan over the last %d days, %d balls across %d sessions. '
            'Distances read as %s and speeds as %s. Medians, with spread as half the '
            'central 80%% of shots. Clubs under 8 shots are marked and never set a '
            'practice plan.' % (tm.get('window_days', 180), tm.get('balls_total', 0),
                               tm.get('sessions_n', 0), u.get('dist', 'unknown'),
                               u.get('speed', 'unknown')))
    probs = tm.get('problems') or []
    if probs:
        note += ' Flagged on import: ' + '; '.join(probs[:3]) + '.'

    strip = statpair('Sessions, 30 days', str(tm.get('sessions_30d', 0)),
                     'Balls, 30 days', str(tm.get('balls_30d', 0)))
    drv = tm.get('driver') or {}
    if drv.get('ball_speed'):
        strip += '\n    ' + statpair('Driver ball speed', '%s mph' % drv['ball_speed'],
                                     'Smash factor', str(drv.get('smash', '—')))

    loop = _loop_rows(tm, stats)
    left = (card('', strip, explain=('smash', 'carry'))
            + card('Session log', '    <ul class="rounds-list" style="margin-top:0">%s</ul>' % sess_rows))
    if loop:
        left += card('Practice against play', loop, explain=('practicegrade',))
    mid = card('Gapping: carry per club', '    <ul class="drows">%s</ul>\n'
                                          '    <p class="vs-note">Median carry · spread across recorded swings</p>' % gap_rows,
               explain=('gapping', 'carry'))
    right = card('Dispersion: left-right spread', '    <ul class="drows">%s</ul>' % disp_rows,
                 explain=('corridor', 'spread'))
    if tm['wedges']:
        right += card('Wedge matrix', wedge, explain=('swinglen',))
    return (plans_cards()
            + '<div class="ggrid3"><div class="gcol">%s</div><div class="gcol">%s</div>'
              '<div class="gcol">%s</div></div>' % (left, mid, right)
            + '<section><p class="vs-note">%s</p></section>' % note)


def page_practice(stats, g):
    """The TrackMan tab. Real measurements once data/trackman.json exists; until
    then SAMPLE numbers, clearly flagged on the page."""
    tm = trackman_data()
    if tm:
        return page_trackman_real(tm, stats)
    gap = [('Dr', 282, 9), ('3w', 258, 8), ('2i', 240, 8), ('4i', 222, 7), ('5i', 212, 6), ('6i', 200, 6),
           ('7i', 188, 5), ('8i', 176, 5), ('9i', 164, 5), ('Pw', 150, 4), ('50\u00b0', 136, 4),
           ('54\u00b0', 120, 4), ('58\u00b0', 105, 4)]
    gap_rows = ''.join(drow(c, rbar(v / 300, 'neu'), f'\u00b1{s} yd', f'{v}') for c, v, s in gap)
    disp = [('Dr', 24, 'right'), ('3w', 19, 'right'), ('5i', 13, 'straight'), ('7i', 9, 'straight'),
            ('Pw', 6, 'left'), ('58\u00b0', 4, 'straight')]
    disp_rows = ''.join(drow(c, rbar(v / 30, '' if v > 15 else 'ok'), f'misses {t}', f'\u00b1{v}')
                        for c, v, t in disp)
    wedge = ('    <div class="table-wrap"><table class="gtable"><thead><tr><th>Club</th><th>1/2</th><th>3/4</th><th>Full</th></tr></thead><tbody>'
             '<tr><td>Pw</td><td>96</td><td>124</td><td class="num num--md">150</td></tr>'
             '<tr><td>50\u00b0</td><td>88</td><td>114</td><td class="num num--md">136</td></tr>'
             '<tr><td>54\u00b0</td><td>76</td><td>101</td><td class="num num--md">120</td></tr>'
             '<tr><td>58\u00b0</td><td>62</td><td>88</td><td class="num num--md">105</td></tr>'
             '</tbody></table></div>\n    <p class="vs-note">Carries in yards; the matrix my 75\u2013125 yd approach bucket trains against</p>')
    sessions = [('Nov 12', 'Wedge block', '84 balls'), ('Nov 8', 'Driver corridor', '52 balls'),
                ('Nov 5', 'Gapping check', '96 balls'), ('Nov 2', 'Wedge block', '74 balls')]
    sess_rows = ''.join(f'<li><span class="course"><b>{t}</b><small>{d} \u00b7 {b}</small></span>'
                        f'<span class="score"><span class="num num--md">\u2192</span></span></li>'
                        for d, t, b in sessions)
    loop = ('    <ul class="leaks">'
            '<li><span class="leak__rank">1</span><div><p class="leak__name">Driving penalties \u2194 driver corridor</p>'
            '<p class="leak__gain">On-course leak: 2.4 strokes a round. Practice target: two-thirds of drives inside \u00b118 yd.</p>'
            + rbar(0.75) + '<p class="leak__basis">Currently \u00b124 yd \u00b7 sample</p></div></li>'
            '<li><span class="leak__rank">2</span><div><p class="leak__name">Short game \u2194 wedge matrix</p>'
            '<p class="leak__gain">On-course leak: 3.2 strokes inside 50 yd. Practice target: half-swing carries within \u00b14 yd.</p>'
            + rbar(0.55) + '<p class="leak__basis">Currently \u00b16 yd \u00b7 sample</p></div></li></ul>')
    left = (card('', statpair('Sessions, 30 days', '6', 'Balls hit', '412')
                 + '\n    ' + statpair('Driver ball speed', '167 mph', 'Smash factor', '1.48').replace('statpair', 'statpair" style="margin-top:1rem'),
                 explain=('smash', 'preview'))
            + card('Session log', f'    <ul class="rounds-list" style="margin-top:0">{sess_rows}</ul>'
                   '\n    <p class="vs-note">Each session will open its own page, like a round</p>')
            + card('Practice against play', loop, explain=('practicegrade',)))
    mid = card('Gapping: carry per club', f'    <ul class="drows">{gap_rows}</ul>'
               '\n    <p class="vs-note">Median carry \u00b7 spread across recorded swings</p>',
               explain=('gapping', 'carry'))
    right = (card('Dispersion: left-right spread', f'    <ul class="drows">{disp_rows}</ul>'
                  '\n    <p class="vs-note">Clubs open their own pages: every swing, drawn out</p>',
                  explain=('corridor', 'spread'))
             + card('Wedge matrix', wedge, explain=('swinglen',)))
    chip = '<p><span class="sample-chip">Preview \u00b7 sample numbers until my first TrackMan session lands</span></p>'
    return plans_cards() + chip + f'<div class="ggrid3"><div class="gcol">{left}</div><div class="gcol">{mid}</div><div class="gcol">{right}</div></div>'


def plans_cards():
    """The issued practice plans (data/golf-plans.json, from Archibald's practice-plan skill)."""
    path = os.path.join(ROOT, 'data', 'golf-plans.json')
    if not os.path.exists(path):
        return ''
    plans = json.load(open(path, encoding='utf-8'))
    if not plans:
        return ''
    cur = plans[0]
    d = date.fromisoformat(cur['date']).strftime('%A, %b %-d')
    where = f' at {cur["location"]}' if cur.get('location') else ''
    bench = ' \u00b7 benchmark session' if cur.get('benchmark') else ''
    rows = ''.join(f'<li><span class="balls">{b["balls"]}</span><span class="body"><b>{b["title"]}.</b> {b["detail"]}'
                   + (f'<span class="tgt">Target: {b["target"]}</span>' if b.get('target') else '')
                   + '</span></li>' for b in cur['blocks'])
    log = []
    for p in plans[:6]:
        dot = ' \u00b7 '
        kind = p['type'].title() + (dot + 'benchmark' if p.get('benchmark') else '')
        sub = date.fromisoformat(p['date']).strftime('%b %-d') + (dot + p['location'] if p.get('location') else '')
        log.append(f'<li><span class="course"><b>{kind}</b><small>{sub}</small></span>'
                   f'<span class="score"><span class="n">{p.get("status", "planned")}</span></span></li>')
    log = ''.join(log)
    current = card(f'Current plan \u00b7 {d}',
                   f'    <p style="margin:0 0 0.8rem;font-size:0.92rem">{cur["type"].title()} session{where}{bench}. '
                   f'Built from the live leak table: {cur.get("focus", "")}.</p>\n'
                   f'    <ul class="plan">{rows}</ul>\n'
                   f'    <p class="vs-note">{cur.get("note", "")}</p>')
    loglist = card('Plan log', f'    <ul class="rounds-list" style="margin-top:0">{log}</ul>',
                   explain=('plans', 'practicegrade'))
    return f'<div class="ggrid"><div class="gcol">{current}</div><div class="gcol">{loglist}</div></div>'



# ---------------------------------------------------------------------------
# the story page: what the numbers mean, what connects to what, what to do
# ---------------------------------------------------------------------------

def para(text):
    return f'    <p class="story-p">{text}</p>\n'


def story_where(stats, g):
    idx = g['revisions'][-1]['index']
    r18 = [r for r in (g.get('recent_rounds') or []) if r.get('holes') == 18 and r.get('score')]
    avg = sum(r['score'] for r in r18) / len(r18) if r18 else None
    sc = stats['scoring']
    gap = abs(stats['sg']['total'])
    out = (f'    <div class="hero-score"><span class="num num--xl">{idx}</span>'
           f'<span class="vs">Handicap Index</span></div>\n')
    bits = [f'My index is {idx}']
    if avg:
        bits.append(f'I shoot about {avg:.0f} on the rounds I post')
    bits.append(f'and on the {stats["rounds_n"]} rounds where every shot was recorded I averaged '
                f'{sc["avg18"]:.1f}, which is {gap:.0f} strokes a round worse than a scratch player '
                'would be from the same places')
    out += para('. '.join(bits[:1]) + ', ' + ', '.join(bits[1:]) + '.')
    out += para('Those three numbers disagree on purpose, and that is the first thing worth '
                'understanding about my own data.')
    out += '    ' + ex('index') + '\n'
    b = sc['bands']
    holes = sum(b.values()) or 1
    out += para(f'Hole by hole, those rounds were {b["birdie"]} birdies and {b["eagle"]} eagle, '
                f'{b["par"]} pars, {b["bogey"]} bogeys and <b>{b["double+"]} doubles or worse</b> '
                f'across {holes} holes. The doubles are {b["double+"] / holes:.0%} of my holes and they '
                'are where the round actually goes. Nothing on this page matters as much as how those '
                'holes start and end.')
    return card('Where I stand', out, cls='gcard--hero')


def story_chain(stats, g):
    steps = [('Every shot', 'start and end position, recorded by the sensors in my grips'),
             ('Expected strokes', 'what a scratch player would need from each of those positions'),
             ('Strokes gained, per shot', 'the difference the shot made, against that standard'),
             ('Four categories', 'driving, approach, short game, putting: every shot lands in one'),
             ('The gap', f'{abs(stats["sg"]["total"]):.0f} strokes a round, which is the four added up'),
             ('Leaks', 'the distance buckets inside those categories that are actually losing strokes'),
             ('Practice', 'the sessions are built from the leak table, in order')]
    items = ''.join(f'<li><span class="step-n">{i}</span><div><b>{n}</b><span>{d}</span></div></li>'
                    for i, (n, d) in enumerate(steps, 1))
    out = para('Everything on this site comes out of one chain. Each link is simple; the confusion comes '
               'from meeting them out of order.')
    out += f'    <ol class="chain">{items}</ol>\n'
    out += '    ' + ex('expected') + '\n    ' + ex('sg') + '\n    ' + ex('categories') + '\n'
    out += para('The handicap is a separate chain that runs alongside it, built from scores rather than '
                'shots. That is why rounds I played without the sensors still move my index but never '
                'appear on the strokes gained pages.')
    out += '    ' + ex('differential') + '\n    ' + ex('scratch') + '\n'
    return card('How one shot becomes a handicap', out)


def story_parts(stats, g):
    sg_pr, ci = stats['sg']['per_round'], (stats['sg'].get('ci') or {})
    d, a, sh, p = stats['driving'], stats['approach'], stats['short'], stats['putting']
    gs = sh.get('updown_greenside') or sh['updown']
    pitch = sh.get('updown_pitch') or {}
    fw = d.get('fairways') or {}
    blocks = []

    def block(key, name, href, lead, extra=''):
        v = sg_pr[key]
        rng = ci.get(key)
        verdict = ('<span class="tag tag--real">established</span>' if decisive(rng)
                   else '<span class="tag">not callable yet</span>')
        return (f'<div class="part"><div class="part-head"><h3><a href="{href}">{name}</a></h3>'
                f'<span class="num num--md">{sg(v)}</span></div>'
                f'<p class="part-rng">{rng_text(rng)} a round {verdict}</p>'
                f'<p class="story-p">{lead}</p>{extra}</div>')

    miss = a.get('miss_dir') or {}
    short_miss = miss.get('short', 0)
    miss_total = sum(miss.values()) or 1
    blocks.append(block(
        'driving', 'Driving', 'golf-driving.html',
        ((f'I hit {fw["hit"]} of {fw["of"]} fairways and my driver goes ' if fw.get('of')
          else 'My driver goes ')
         + f'{d["driver_median_yd"]} yards, which is not the problem. The problem is '
           f'{d["tee_penalties"]} penalty balls off the tee in {d["tee_shots"]} tee shots. '
           'Distance I have; the ball being in play I do not.'),
        '    ' + ex('penalty')))
    blocks.append(block(
        'approach', 'Approach', 'golf-approach.html',
        f'I hit {a["gir_pct"]}% of greens against about {SCRATCH["gir_pct"]}% for scratch, and when I do '
        f'hit one I am {a["prox_gir_ft"]} feet away. No single yardage stands out as the villain. What '
        f'does stand out is the direction: {short_miss} of my {miss_total} misses are <b>short</b>, more '
        f'than every other miss put together, and the pattern sits {a.get("dispersion", {}).get("tendency", "")}.',
        '    ' + ex('gir') + '\n    ' + ex('prox') + '\n    ' + ex('dispersion')))
    short_lead = (f'This is the biggest single hole in my game and it follows directly from the one '
                  f'above. Missing {100 - a["gir_pct"]}% of greens means about '
                  f'{round((100 - a["gir_pct"]) / 100 * 18)} chances a round to save par with a chip and '
                  'a putt. ')
    if gs.get('of'):
        short_lead += (f'I convert {round(gs["made"] / gs["of"] * 100)}% of the ones inside 30 yards, '
                       f'{gs["made"]} of {gs["of"]}, where scratch converts about '
                       f'{SCRATCH["updown_pct"]}%.')
        if pitch.get('of'):
            short_lead += f' From 30 to 50 yards I am {pitch["made"]} of {pitch["of"]}.'
    else:
        short_lead += 'No greenside chances have been recorded yet, so there is no conversion rate to show.'
    blocks.append(block('short', 'Short game', 'golf-short-game.html', short_lead, '    ' + ex('updown')))
    blocks.append(block(
        'putting', 'Putting', 'golf-putting.html',
        f'I take {p["putts_round"]:.0f} putts a round, which sounds bad until you remember I am putting '
        f'from further away than a scratch player because of everything above. My {p["three_putts"]} '
        f'three-putts followed first putts averaging {p["three_putt_first_ft"]} feet, against '
        f'{p["two_putt_first_ft"]} feet on the holes I two-putted.',
        '    ' + ex('threeputt')))
    out = para('Four parts, in the order the shots happen. Two of them are established findings and two '
               'are not yet, which matters more than the headline numbers.')
    out += '    ' + ex('range') + '\n'
    out += f'    <div class="parts">{"".join(blocks)}</div>\n'
    return card('The four parts, and how they feed each other', out)


def story_leaks(stats):
    leaks = stats.get('leaks') or []
    if not leaks:
        return ''
    out = para('Narrowed from the four parts down to the buckets actually losing the strokes, in order, '
               'priced per round.')
    rows = ''.join(f'<li><span class="leak__rank">{i}</span><div><p class="leak__name">{l["name"]}</p>'
                   f'<p class="leak__gain">About <b>{abs(l["per_round"]):.1f} strokes a round</b>, '
                   f'{l["share"]}% of everything available. {l["basis"]}.</p>'
                   + rbar(l['share'] / 100) + '</div></li>'
                   for i, l in enumerate(leaks, 1))
    out += f'    <ol class="leaks">{rows}</ol>\n'
    out += '    ' + ex('leak') + '\n    ' + ex('thin') + '\n    ' + ex('plans') + '\n'
    return card('Where the strokes actually go', out)


def story_plan(stats, g):
    leaks = stats.get('leaks') or []
    d, a, sh = stats['driving'], stats['approach'], stats['short']
    gs = sh.get('updown_greenside') or sh['updown']
    rounds18 = stats['holes'] / 18
    out = para('Three things, in this order, because this is the order the data puts them in. Each one '
               'has a number attached, so it is possible to be wrong about it later.')
    goals, gained = [], 0.0
    pens = d['tee_penalties']
    if pens:
        half = pens / 2.0
        goals.append(('Put the tee ball in play',
                      f'{pens} penalty tee shots in {d["tee_shots"]} swings is {pens / rounds18:.1f} a '
                      f'round. Halving that to {half:.0f} is worth about '
                      f'{(pens - half) / rounds18:.1f} strokes a round on its own.',
                      f'{pens / d["tee_shots"]:.0%} of tee shots \u2192 {pens / d["tee_shots"] / 2:.0%}'))
        gained += (pens - half) / rounds18
    if gs.get('of'):
        now = gs['made'] / gs['of']
        target = min(0.45, now + 0.12)
        extra = (target - now) * gs['of']
        goals.append(('Get up and down from inside 30 yards',
                      f'{round(now * 100)}% now against about {SCRATCH["updown_pct"]}% for scratch. '
                      f'Getting to {round(target * 100)}% would have saved {extra:.0f} shots over these '
                      f'rounds, about {extra / rounds18:.1f} a round.',
                      f'{round(now * 100)}% \u2192 {round(target * 100)}%'))
        gained += extra / rounds18
    miss = a.get('miss_dir') or {}
    shorts = miss.get('short', 0)
    if shorts and shorts >= max([v for k, v in miss.items() if k != 'short'] or [0]):
        goals.append(('Take enough club',
                      f'{shorts} of {sum(miss.values())} approach misses are short. That is a club '
                      'selection habit, not a swing fault, and it is the cheapest thing on this list to '
                      f'change. It also feeds the item above: short misses leave the longest chips.',
                      'one more club'))
    items = ''.join(f'<li><span class="step-n">{i}</span><div><b>{t}</b><span>{why}</span>'
                    f'<span class="goal-move">{mv}</span></div></li>'
                    for i, (t, why, mv) in enumerate(goals, 1))
    out += f'    <ol class="chain chain--goals">{items}</ol>\n'
    if gained:
        avg = stats['scoring']['avg18']
        out += para(f'The two I can put a number on are worth about {gained:.1f} strokes a round between '
                    f'them, which turns the {avg:.0f} I average with shots tracked into '
                    f'{an(avg - gained)}.'
                    + (f' Closing those buckets all the way to scratch would be '
                       f'{sum(abs(l["per_round"]) for l in leaks[:3]):.1f}, but that is the ceiling rather '
                       'than a plan.' if leaks else ''))
    out += para('Nothing here says swing differently. Everything here says play differently and practise '
                'the two shots that keep costing me, which is what the practice plans are built from.')
    return card('What I am working on, and why', out)


def story_limits(stats, g):
    q = stats.get('quality') or {}
    out = para(f'This is built on {stats["rounds_n"]} rounds and {stats["holes"]} holes. That is enough to '
               'be useful and not enough to be certain, and the honest version of this page says which is '
               'which.')
    limits = [
        ('Two of the four parts are not callable yet',
         'Driving and putting both have ranges that still cross zero. They may be fine, they may be bad, '
         'and more rounds will say.'),
        ('Every lie is assumed',
         'The data records where the ball was, not what it was sitting on. A chip from thick rough and a '
         'chip from the fairway are scored the same, so my short game number is probably a little harsher '
         'than the truth.'),
        ('Distances are raw GPS',
         'Mine are measured from where the ball started to where it stopped, so they include roll. The '
         'figures inside the Arccos app are modelled and run longer.'),
        ('Some rounds are missing',
         'Only the rounds where I wore the sensors are here. Rounds without them still move my handicap '
         'and still appear on the rounds page, but they cannot be broken down.'),
        ('The scratch baseline is calibrated, not published',
         'The expected-strokes table behind all of this was assembled from public sources and tuned to '
         'agree with Arccos on these same rounds, so it is a reasonable standard rather than an '
         'independent one.'),
    ]
    if q.get('excluded_rounds'):
        limits.append(('A round was thrown out',
                       f'{", ".join(q["excluded_rounds"])}: the shot data disagreed with the scorecard, '
                       'so it is excluded from every number here.'))
    out += '    <dl class="limits">' + ''.join(f'<dt>{t}</dt><dd>{b}</dd>' for t, b in limits) + '</dl>\n'
    out += para('When any of that changes, these pages change with it. They rebuild from the data every '
                'morning, so nothing here is a claim I wrote once and left standing.')
    return card('What this data cannot tell me', out)


def page_story(stats, g):
    return (story_where(stats, g) + story_chain(stats, g) + story_parts(stats, g)
            + story_leaks(stats) + story_plan(stats, g) + story_limits(stats, g))


SUBPAGES = {
    'golf-story.html': ('My game', 'The whole picture in plain language: what every number means, what connects to what, and what I am working on.', page_story),
    'golf-driving.html': ('Driving', 'Off the tee: distance, penalties and the misses that cost strokes.', page_driving),
    'golf-approach.html': ('Approach', 'Approach play by distance: strokes gained, proximity and greens hit, against scratch.', page_approach),
    'golf-short-game.html': ('Short game', 'Inside 50 yards: up and down rate and where strokes leak around the green.', page_short),
    'golf-putting.html': ('Putting', 'Make rates by distance against a scratch player, and what precedes a three-putt.', page_putting),
    'golf-rounds.html': ('Rounds & scoring', 'Every sensor-tracked round, and scoring by hole type and length.', page_rounds),
    'golf-trackman.html': ('TrackMan', 'Every practice session on TrackMan: speeds, carries, gapping and dispersion per club.', page_practice),
}


def write_page(fname, title, ogtitle, desc, content, g, stats):
    index = g['revisions'][-1]['index']
    note = (f'{stats["source"]} I wear the sensors every round now, so this fills in as I play. ' if stats else '')
    excluded = ((stats or {}).get('quality') or {}).get('excluded_rounds') or []
    if excluded:
        note += (f'{len(excluded)} round{"" if len(excluded) == 1 else "s"} '
                 f'({", ".join(excluded)}) {"is" if len(excluded) == 1 else "are"} left out because the '
                 f'shot data does not match the scorecard. ')
    note += (f'Handicap and scoring history come from my GHIN record, updated daily. '
             f'<a href="index.html">jackraney.com</a> · <a href="about.html">about me</a>')
    html = SHELL.format(title=title, ogtitle=ogtitle, desc=desc, slug=fname.replace('.html', ''),
                        index=index, nav=nav_links(fname),
                        rounds_pill=f'{g["rounds_last_12_months"]} rounds \u00b7 12 mo',
                        content=content, note=note)
    path = os.path.join(ROOT, fname)
    old = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
    if html != old:
        open(path, 'w', encoding='utf-8').write(html)
        print(fname, 'updated')


def main():
    gpath = os.path.join(ROOT, 'data', 'golf.json')
    if not os.path.exists(gpath):
        print('no data/golf.json; nothing to do')
        return
    g = json.load(open(gpath, encoding='utf-8'))
    spath = os.path.join(ROOT, 'data', 'golf-stats.json')
    stats = json.load(open(spath, encoding='utf-8')) if os.path.exists(spath) else None
    if stats:
        hub = (f'<section class="span2" style="margin-bottom:1.3rem">{briefing(stats, g)}</section>'
               f'<div class="ggrid">'
               f'<div class="gcol">{hero_card(stats, g)}{sg_card(stats)}</div>'
               f'<div class="gcol">{scoring_card(stats)}{leaks_card(stats)}</div>'
               f'<section class="span2">{handicap_card(g)}</section>'
               f'<div class="gcol">{bypar_card(g)}</div>'
               f'<div class="gcol">{highlights_card(stats)}</div>'
               f'</div>')
    else:
        hub = f'<div class="ggrid"><section class="span2">{handicap_card(g)}</section><div class="gcol">{bypar_card(g)}</div></div>'
    write_page('golf.html', 'Road to scratch · Jack Raney', 'Road to scratch',
               'Jack Raney’s golf: working toward scratch, every round and practice session measured. Updates itself daily.',
               hub, g, stats)
    if stats:
        for fname, (title, desc, render) in SUBPAGES.items():
            write_page(fname, f'{title} · Road to scratch · Jack Raney', title, desc, render(stats, g), g, stats)


if __name__ == '__main__':
    main()
