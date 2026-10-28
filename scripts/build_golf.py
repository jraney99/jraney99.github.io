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

PAGES = [('golf.html', 'Overview'), ('golf-driving.html', 'Driving'), ('golf-approach.html', 'Approach'),
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


def card(section, inner, cls='', icon=''):
    head = f'  <h2 class="gsect">{section}</h2>\n' if section else ''
    return f'<section>\n{head}  <div class="gcard {cls}">\n{inner}\n  </div>\n</section>\n'


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
    return card('Scoring', inner, cls='gcard--hero')


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
    return card('Strokes gained breakdown', inner)


def leaks_card(stats):
    rows = []
    for i, l in enumerate(stats['leaks'], 1):
        rows.append(f'<li><span class="leak__rank">{i}</span><div><p class="leak__name">{l["name"]}</p>'
                    f'<p class="leak__gain">Fixing this is worth about {abs(l["per_round"]):.1f} strokes a round.</p>'
                    + rbar(l['share'] / 100)
                    + f'<p class="leak__basis">{l["share"]}% of the focus-area upside · {l["basis"]}</p></div></li>')
    return card('Where to focus', f'    <ol class="leaks">{"".join(rows)}</ol>')


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
            + card('', statpair('Tee-shot penalties', d['tee_penalties'], 'Fairways', f'{fw["hit"] / fw["of"]:.0%}')))
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
    return f'<div class="ggrid"><div class="gcol">{left}</div><div class="gcol">{right}</div></div>'


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
    mid = card('SG by distance (yd)', f'    <ul class="plan">{rows}</ul>')
    right = card('Where approach shots finish', missgrid)
    return f'<div class="ggrid3"><div class="gcol">{left}</div><div class="gcol">{mid}</div><div class="gcol">{right}</div></div>'


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
    right = card('SG by distance (yd)', f'    <ul class="plan">{rows}</ul>')
    return f'<div class="ggrid"><div class="gcol">{left}</div><div class="gcol">{right}</div></div>'


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
                   'is measured.</p>')
    left = (focus_card(f'{worst} ft putts', 'Tighten this band first; the rest of my putting holds up against scratch.',
                       sg(p['sg_round']), 'Strokes/rnd')
            + card('', statpair('Putts per round', p['putts_round'], '3-putts/rnd', round(p['three_putts'] / (stats['holes'] / 18), 1))))
    mid = (card('SG by putt distance', f'    <span class="opp-chip">#1 opportunity: {worst} ft</span>\n    <ul class="drows">{sg_rows}</ul>')
           + card('Make rate by distance', f'    <ul class="drows">{"".join(make_rows)}</ul>\n'
                  '    <p class="vs-note">▏ marks a scratch player’s make rate (Arccos data)</p>'))
    right = autopsy
    return f'<div class="ggrid3"><div class="gcol">{left}</div><div class="gcol">{mid}</div><div class="gcol">{right}</div></div>'


def page_rounds(stats, g):
    idx = num(g['revisions'][-1]['index'])
    tracked = {r['date'] for r in stats['rounds']}
    grows = []
    for r in (g.get('recent_rounds') or []):
        if not r.get('score'):
            continue
        d = date.fromisoformat(r['date']).strftime('%b %d, %Y')
        diff = r.get('differential')
        dcls = 'pos' if diff is not None and diff <= idx else 'warn'
        has_shots = 'Yes' if r['date'] in tracked else '\u2013'
        name = r.get('course') or '\u2013'
        grows.append(f'<tr><td>{d}</td><td>{name}</td><td>{r["holes"]}</td><td class="num num--md">{r["score"]}</td>'
                     f'<td><span class="{dcls}">{diff:.1f}</span></td><td>{has_shots}</td></tr>')
    ghin_table = card('Latest posted rounds (GHIN)',
                      '    <div class="table-wrap"><table class="gtable"><thead><tr><th>Date</th><th>Course</th><th>Holes</th>'
                      '<th>Score</th><th>Differential</th><th>Shots tracked</th></tr></thead><tbody>'
                      + ''.join(grows) + '</tbody></table></div>\n'
                      '    <p class="vs-note">A differential at or under my index beat my handicap. Rounds without '
                      'sensor shots count for scoring and handicap, but not for the strokes-gained pages.</p>')
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


def page_trackman_real(tm, stats):
    """The TrackMan tab on real measurements."""
    clubs = [c for c in tm['clubs'] if c.get('carry')]
    longest = max([c['carry'] for c in clubs] or [1])
    gap_rows = ''.join(
        drow(c['club'], rbar(c['carry'] / longest, 'neu'),
             ('±%s yd' % c['carry_spread']) if c.get('carry_spread') else ('%d shots' % c['n']),
             str(c['carry']), c['thin'])
        for c in clubs)

    withside = [c for c in tm['clubs'] if c.get('side_spread') is not None]
    widest = max([c['side_spread'] for c in withside] or [1]) or 1
    disp_rows = ''.join(
        drow(c['club'], rbar(c['side_spread'] / widest, '' if c['side_spread'] > 15 else 'ok'),
             'misses %s' % c['side_bias'], '±%s' % c['side_spread'], c['thin'])
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
           (s['grade'] or {}).get('summary', '') if s.get('grade') else '—')
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
    left = card('', strip) + card('Session log', '    <ul class="rounds-list" style="margin-top:0">%s</ul>' % sess_rows)
    if loop:
        left += card('Practice against play', loop)
    mid = card('Gapping: carry per club', '    <ul class="drows">%s</ul>\n'
                                          '    <p class="vs-note">Median carry · spread across recorded swings</p>' % gap_rows)
    right = card('Dispersion: left-right spread', '    <ul class="drows">%s</ul>' % disp_rows)
    if tm['wedges']:
        right += card('Wedge matrix', wedge)
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
                 + '\n    ' + statpair('Driver ball speed', '167 mph', 'Smash factor', '1.48').replace('statpair', 'statpair" style="margin-top:1rem'))
            + card('Session log', f'    <ul class="rounds-list" style="margin-top:0">{sess_rows}</ul>'
                   '\n    <p class="vs-note">Each session will open its own page, like a round</p>')
            + card('Practice against play', loop))
    mid = card('Gapping: carry per club', f'    <ul class="drows">{gap_rows}</ul>'
               '\n    <p class="vs-note">Median carry \u00b7 spread across recorded swings</p>')
    right = (card('Dispersion: left-right spread', f'    <ul class="drows">{disp_rows}</ul>'
                  '\n    <p class="vs-note">Clubs open their own pages: every swing, drawn out</p>')
             + card('Wedge matrix', wedge))
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
    loglist = card('Plan log', f'    <ul class="rounds-list" style="margin-top:0">{log}</ul>')
    return f'<div class="ggrid"><div class="gcol">{current}</div><div class="gcol">{loglist}</div></div>'



SUBPAGES = {
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
