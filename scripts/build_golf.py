"""Render the golf section: golf.html (hub) plus the deep pages, from data/golf.json
(written daily by Archibald's ghin-handicap skill) and data/golf-stats.json (computed
from sensor-tracked rounds; strokes gained vs a scratch baseline calibrated to Arccos).

Run from the repo root: python3 scripts/build_golf.py
On golf.html only the region between the golf:start and golf:end markers is rewritten.
The golf-*.html pages are generated whole, inheriting the site chrome from golf.html.
"""
import json
import math
import os
import re
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'golf.html')
START, END = '<!-- golf:start -->', '<!-- golf:end -->'
PAR_HOLES = {'3': 4, '4': 10, '5': 4}  # a typical 18-hole card


def num(v):
    return -float(v[1:]) if str(v).startswith('+') else float(v)


def show(v):
    return f'+{abs(v):.1f}' if v < 0 else f'{v:.1f}'


def month(d):
    return date.fromisoformat(d).strftime('%b %Y')


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
    return ('        <div class="dca-scroll"><svg viewBox="0 0 720 312" role="img" class="dca-chart" '
            f'aria-label="Handicap Index from {month(revs[0]["date"])} to {month(today)}">\n' + '\n'.join(out) + '\n</svg></div>\n')


def body(g, stats=None):
    revs, today = g['revisions'], g['updated']
    cur = num(revs[-1]['index'])
    year_ago = date.fromisoformat(today).replace(year=date.fromisoformat(today).year - 1).isoformat()
    low = min(num(r['index']) for r in revs if r['date'] >= year_ago)
    best = g.get('best_differential')
    figs = [('Handicap Index', show(cur)), ('Low, last 12 months', show(low)),
            ('Rounds posted, last 12 months', str(g['rounds_last_12_months']))]
    if best is not None:
        figs.append(('Best round differential', f'\u2212{abs(best):.1f}' if best < 0 else f'{best:.1f}'))
    out = ['        <dl class="figures figures--4">\n']
    out += [f'          <div><dt>{t}</dt><dd>{v}</dd></div>\n' for t, v in figs]
    out.append('        </dl>\n')
    out.append('        <figure class="exhibit">\n          <figcaption class="exhibit__head"><span class="label">Exhibit 1</span>'
               '<span class="exhibit__title">My Handicap Index, every revision</span></figcaption>\n')
    out.append(chart(revs, today))
    out.append('          <p class="exhibit__note">Lower is better. Scratch is 0; a round differential below 0 beat scratch. On a phone, swipe the chart sideways.</p>\n'
               '        </figure>\n')
    if stats:
        out.append(hub_stats(stats))
    par = g.get('by_par') or {}
    if par:
        rows, per_round = [], {}
        for p in ('3', '4', '5'):
            if p in par:
                per_round[p] = par[p]['avg_over_par'] * PAR_HOLES[p]
                rows.append(f'<tr><td>Par {p}s</td><td>{par[p]["holes"]}</td><td>+{par[p]["avg_over_par"]:.2f}</td>'
                            f'<td>+{per_round[p]:.1f}</td></tr>')
        worst = max(per_round, key=per_round.get)
        rest = sum(v for k, v in per_round.items() if k != worst)
        lead = (f'Par {worst}s cost me the most: about {per_round[worst]:.0f} strokes over par on a typical card'
                + (f', more than the other holes combined ({rest:.0f}).' if per_round[worst] > rest else '.'))
        out.append(f'        <div class="prose"><h2>Where the strokes go</h2><p>{lead}</p></div>\n')
        out.append('        <figure class="exhibit exhibit--narrow"><figcaption class="exhibit__head"><span class="label">Exhibit 2</span>'
                   '<span class="exhibit__title">Average score against par, by hole type</span></figcaption>\n'
                   '          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">Hole</th><th scope="col">Holes played</th>'
                   '<th scope="col">Over par, per hole</th><th scope="col">Over par, per round</th></tr></thead><tbody>'
                   + ''.join(rows) + '</tbody></table></div>\n'
                   f'          <p class="exhibit__note">From the {g["scoring_rounds"]} rounds I posted hole by hole. “Per round” assumes a '
                   'typical card of four par 3s, ten par 4s and four par 5s. Scores are adjusted for handicap posting.</p>\n'
                   '        </figure>\n')
    t = {} if stats else (g.get('tracked') or {})
    bits = []
    if t.get('fairways', [0, 0])[1] >= 30:
        bits.append(f'fairways hit {t["fairways"][0] / t["fairways"][1]:.0%} ({t["fairways"][1]} holes)')
    if t.get('greens', [0, 0])[1] >= 30:
        bits.append(f'greens in regulation {t["greens"][0] / t["greens"][1]:.0%} ({t["greens"][1]} holes)')
    if t.get('putts', [0, 0])[1] >= 30:
        bits.append(f'{t["putts"][0] / t["putts"][1]:.2f} putts per hole ({t["putts"][1]} holes)')
    if bits:
        out.append(f'        <div class="prose"><p>On the holes where I also tracked stats: {", ".join(bits)}.</p></div>\n')
    a = {} if stats else (g.get('arccos') or {})
    cats = a.get('categories') or {}
    if cats:
        rows = ''.join(f'<tr><td>{k}</td><td>{"+" if v > 0 else ("−" if v < 0 else "")}{abs(v):.1f}</td></tr>' for k, v in cats.items())
        out.append('        <figure class="exhibit exhibit--narrow"><figcaption class="exhibit__head"><span class="label">Exhibit 3</span>'
                   '<span class="exhibit__title">Strokes gained per round, from Arccos</span></figcaption>\n'
                   '          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">Part of the game</th>'
                   '<th scope="col">Strokes gained</th></tr></thead><tbody>' + rows + '</tbody></table></div>\n'
                   f'          <p class="exhibit__note">From {a.get("rounds")} rounds tracked with Arccos sensors, compared with a '
                   'scratch golfer. Negative means strokes lost.</p>\n        </figure>\n')
    elif not stats:
        out.append('        <div class="prose"><p>Strokes gained, which shows exactly where shots are lost off the tee, on approach, '
                   'around the green and on the greens, will appear here once enough rounds are tracked with Arccos.</p></div>\n')
    practice = []
    if g.get('courses_played'):
        practice.append(f'I’ve played {g["courses_played"]} different courses')
    if practice:
        out.append('        <div class="prose"><p>' + ' '.join(practice) + ', and counting.</p></div>\n')
    out.append(f'        <p class="note">From my GHIN record: every Handicap Index revision and every posted score. '
               f'Course names are left out. Updated daily; last checked {date.fromisoformat(today).strftime("%B")} '
               f'{date.fromisoformat(today).day}, {today[:4]}.</p>\n')
    html = ''.join(out)
    if stats:
        html = golf_nav('golf.html') + html
    counter = iter(range(1, 99))
    return re.sub(r'(<span class="label">)Exhibit \d+(</span>)',
                  lambda m: f'{m.group(1)}Exhibit {next(counter)}{m.group(2)}', html)


def main():
    path = os.path.join(ROOT, 'data', 'golf.json')
    if not os.path.exists(path) or not os.path.exists(PAGE):
        print('no data/golf.json or golf.html; nothing to do')
        return
    stats = None
    spath = os.path.join(ROOT, 'data', 'golf-stats.json')
    if os.path.exists(spath):
        stats = json.load(open(spath, encoding='utf-8'))
    page = open(PAGE, encoding='utf-8').read()
    a, b = page.index(START) + len(START), page.index(END)
    new = page[:a] + '\n' + body(json.load(open(path, encoding='utf-8')), stats) + '        ' + page[b:]
    if new != page:
        open(PAGE, 'w', encoding='utf-8').write(new)
        print('golf.html updated')
    else:
        print('golf.html unchanged')
    if stats:
        write_subpages(new, stats)





# ---------------------------------------------------------------------------
# The stats-driven section (hub blocks + deep pages), from data/golf-stats.json.
# Layout copied from Arccos's web dashboard at Jack's request, in the site's skin.
# ---------------------------------------------------------------------------

PAGES = [('golf.html', 'Overview'), ('golf-driving.html', 'Driving'), ('golf-approach.html', 'Approach'),
         ('golf-short-game.html', 'Short game'), ('golf-putting.html', 'Putting'),
         ('golf-rounds.html', 'Rounds'), ('golf-practice.html', 'Practice')]
CATS = [('driving', 'Off the tee', 'golf-driving.html'), ('approach', 'Approach', 'golf-approach.html'),
        ('short', 'Around the green', 'golf-short-game.html'), ('putting', 'Putting', 'golf-putting.html')]


def sg(v, dec=1):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.{dec}f}'


def golf_nav(current):
    links = ''.join(f'<strong>{t}</strong>' if p == current else f'<a href="{p}">{t}</a>'
                    for p, t in PAGES)
    return f'        <nav class="golf-nav" aria-label="Golf section">{links}</nav>\n'


def source_note(stats, extra=''):
    return (f'        <p class="note">{stats["source"]}. I wear the sensors every round now, so this fills in as I play. '
            f'{extra}Updated automatically.</p>\n')


def ledger(stats):
    worst = stats['sg']['focus']
    rows = []
    for key, name, href in CATS:
        v = stats['sg']['per_round'][key]
        w = min(abs(v) / 5 * 100, 100)
        cls = ' class="worst"' if key == worst else ''
        rows.append(f'<li{cls}><a class="cat" href="{href}">{name}</a>'
                    f'<span class="bar"><i style="width:{w:.0f}%"></i></span><span class="sg">{sg(v)}</span>'
                    f'<a class="open" href="{href}">Open →</a></li>')
    return ('        <figure class="exhibit">\n          <figcaption class="exhibit__head"><span class="label">Exhibit 2</span>'
            '<span class="exhibit__title">The gap to scratch, in strokes per round</span></figcaption>\n'
            '          <ol class="gap-ledger">' + ''.join(rows) + '</ol>\n'
            f'          <p class="exhibit__note">Strokes gained against a scratch player, {sg(stats["sg"]["total"])} per round in all. '
            'The yellow bar is the biggest gap. Each line opens the detail page.</p>\n        </figure>\n')


def leaks_block(stats):
    cards = []
    for i, l in enumerate(stats['leaks'], 1):
        cards.append(f'<li><span class="leak__rank">{i}</span><div><p class="leak__name">{l["name"]}</p>'
                     f'<p class="leak__gain">Fixing this is worth about {abs(l["per_round"]):.1f} strokes a round.</p>'
                     f'<span class="bar"><i style="width:{l["share"]}%"></i></span>'
                     f'<p class="leak__basis">{l["share"]}% of the focus-area upside · {l["basis"]}</p></div></li>')
    return ('        <div class="prose"><h2>Where to focus</h2></div>\n'
            '        <ol class="leaks">' + ''.join(cards) + '</ol>\n')


def bands_row(stats):
    b, total = stats['scoring']['bands'], sum(stats['scoring']['bands'].values())
    cells = ''.join(f'<div><dt>{k.replace("+", " or worse").title()}</dt><dd>{v}<small> {v / total:.0%}</small></dd></div>'
                    for k, v in b.items())
    return f'        <dl class="figures figures--5 bands">{cells}</dl>\n'


def rounds_table(stats, limit=5):
    rows = []
    for r in stats['rounds'][:limit]:
        tot = sum(r['sg'].values())
        d = date.fromisoformat(r['date']).strftime('%b %d')
        rows.append(f'<tr><td>{d}</td><td>{r["course"]}</td><td>{r["score"]}{"" if r["holes"] == 18 else " (9)"}</td>'
                    f'<td>{sg(r["score"] - r["par"], 0)}</td><td>{sg(tot)}</td></tr>')
    return ('        <figure class="exhibit"><figcaption class="exhibit__head"><span class="label">Exhibit 3</span>'
            '<span class="exhibit__title">Sensor-tracked rounds</span></figcaption>\n'
            '          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">Date</th><th scope="col">Course</th>'
            '<th scope="col">Score</th><th scope="col">To par</th><th scope="col">SG vs scratch</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>\n'
            '          <p class="exhibit__note">Every shot recorded by Arccos sensors. <a class="inline-link" href="golf-rounds.html">All rounds and scoring detail →</a></p>\n'
            '        </figure>\n')


def hub_stats(stats):
    s = stats['scoring']
    figs = (f'        <dl class="figures figures--4">'
            f'<div><dt>Scoring average</dt><dd>{s["avg18"]}</dd></div>'
            f'<div><dt>Gap to scratch</dt><dd>{abs(stats["sg"]["total"]):.1f} strokes</dd></div>'
            f'<div><dt>Greens in regulation</dt><dd>{stats["approach"]["gir_pct"]}%</dd></div>'
            f'<div><dt>Putts per round</dt><dd>{stats["putting"]["putts_round"]}</dd></div></dl>\n')
    return figs + bands_row(stats) + ledger(stats) + leaks_block(stats) + rounds_table(stats)


def bucket_table(buckets, unit, head, n_key='shots'):
    rows = []
    for b, v in buckets.items():
        w = min(abs(v['sg_round']) / 2.5 * 100, 100)
        cls = ' class="pos"' if v['sg_round'] > 0 else ''
        rows.append(f'<tr><td>{b} {unit}</td><td>{v[n_key]}</td>'
                    f'<td><span class="bar bar--table"><i{cls} style="width:{w:.0f}%"></i></span></td><td>{sg(v["sg_round"])}</td></tr>')
    return ('          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">' + head + '</th>'
            '<th scope="col">Shots</th><th scope="col"></th><th scope="col">SG per round</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>\n')


def page_driving(stats):
    d = stats['driving']
    fw = d['fairways']
    return (f'        <dl class="figures figures--4">'
            f'<div><dt>Strokes gained, per round</dt><dd>{sg(d["sg_round"])}</dd></div>'
            f'<div><dt>Tee-shot penalties</dt><dd>{stats["leaks"][0]["basis"].split()[0] if "tee-shot" in stats["leaks"][0]["basis"] else d["penalties"]}</dd></div>'
            f'<div><dt>Average drive</dt><dd>{d["avg_yd"]} yd</dd></div>'
            f'<div><dt>Longest drive</dt><dd>{d["longest_yd"]} yd</dd></div></dl>\n'
            f'        <div class="prose"><h2>What matters off the tee</h2>'
            f'<p>I hit {fw["hit"]} of {fw["of"]} fairways ({fw["hit"] / fw["of"]:.0%}). That number barely matters: in Shot Scope’s data, '
            f'fairway percentage is almost flat from scratch to a 20 handicap. What separates handicaps off the tee is the disaster rate, '
            f'penalty balls and the spots you cannot advance from. That is where my strokes go: the penalties alone cost about '
            f'{abs(stats["leaks"][0]["per_round"]):.1f} strokes a round when they come from the tee.</p></div>\n')


def page_approach(stats):
    a = stats['approach']
    m = a['miss_dir']
    total_attacks = sum(m.values()) + round(a['gir_pct'] / 100 * stats['holes'])
    disp = a.get('dispersion') or {}
    miss = (f'        <figure class="exhibit exhibit--narrow"><figcaption class="exhibit__head"><span class="label">Exhibit 2</span>'
            '<span class="exhibit__title">Where approach shots finish</span></figcaption>\n'
            f'          <div class="miss-grid">'
            f'<span class="miss miss--long">Long<b>{m["long"]}</b></span>'
            f'<span class="miss miss--left">Left<b>{m["left"]}</b></span>'
            f'<span class="miss miss--gir">On the green<b>{a["gir_pct"]}%</b></span>'
            f'<span class="miss miss--right">Right<b>{m["right"]}</b></span>'
            f'<span class="miss miss--short">Short<b>{m["short"]}</b></span></div>\n'
            f'          <p class="exhibit__note">Missed greens by direction, {stats["holes"]} holes. Typical spread: about '
            f'±{disp.get("lateral_sd", "?")} yd side to side, ±{disp.get("depth_sd", "?")} yd long and short; '
            f'the usual miss is {disp.get("tendency", "?")}.</p>\n        </figure>\n')
    return (f'        <dl class="figures figures--4">'
            f'<div><dt>Strokes gained, per round</dt><dd>{sg(a["sg_round"])}</dd></div>'
            f'<div><dt>Greens in regulation</dt><dd>{a["gir_pct"]}%</dd></div>'
            f'<div><dt>Proximity, greens hit</dt><dd>{a["prox_gir_ft"]} ft</dd></div>'
            f'<div><dt>Proximity, all</dt><dd>{a["prox_all_ft"]} ft</dd></div></dl>\n'
            '        <figure class="exhibit"><figcaption class="exhibit__head"><span class="label">Exhibit 1</span>'
            '<span class="exhibit__title">Strokes gained by distance</span></figcaption>\n'
            + bucket_table(a['buckets'], 'yd', 'From') +
            '          <p class="exhibit__note">A scratch golfer hits about two thirds of greens from 75–125 yd. '
            'The deepest bars are where practice pays.</p>\n        </figure>\n' + miss)


def page_short(stats):
    s = stats['short']
    ud = s['updown']
    disp = s.get('dispersion') or {}
    return (f'        <dl class="figures figures--3">'
            f'<div><dt>Strokes gained, per round</dt><dd>{sg(s["sg_round"])}</dd></div>'
            f'<div><dt>Up and down</dt><dd>{ud["made"]} of {ud["of"]}</dd></div>'
            f'<div><dt>Usual miss</dt><dd>{(disp.get("tendency") or "?").title()}</dd></div></dl>\n'
            f'        <div class="prose"><p>This is my biggest gap to scratch. A scratch player gets up and down a little over half '
            f'the time inside 50 yards; I am at {ud["made"] / ud["of"]:.0%} on these rounds.</p></div>\n'
            '        <figure class="exhibit"><figcaption class="exhibit__head"><span class="label">Exhibit 1</span>'
            '<span class="exhibit__title">Strokes gained by distance</span></figcaption>\n'
            + bucket_table(s['buckets'], 'yd', 'From') + '        </figure>\n')


def page_putting(stats):
    p = stats['putting']
    rows = []
    for b, v in p['buckets'].items():
        delta = v['made_pct'] - (v['scratch_pct'] or 0)
        rows.append(f'<tr><td>{b} ft</td><td>{v["n"]}</td><td>{v["made_pct"]}%</td><td>{v["scratch_pct"]}%</td>'
                    f'<td>{sg(delta, 0)}%</td><td>{sg(v["sg_round"])}</td></tr>')
    lag_rows = ''.join(f'<tr><td>{b} ft</td><td>{v["n"]}</td><td>{v["avg_leave_ft"]} ft</td><td>{v["inside3_pct"]}%</td></tr>'
                       for b, v in p['lag'].items())
    autopsy = (f'        <div class="prose"><h2>Three-putt autopsy</h2>'
               f'<p>{p["three_putts"]} three-putts in these rounds, and they share one cause: lag distance. My first putt on '
               f'three-putt holes averaged {p["three_putt_first_ft"]} feet, against {p["two_putt_first_ft"]} feet on two-putt holes. '
               f'The fix is not holing more putts, it is distance control from 25 feet and out.</p></div>\n')
    return (f'        <dl class="figures figures--3">'
            f'<div><dt>Strokes gained, per round</dt><dd>{sg(p["sg_round"])}</dd></div>'
            f'<div><dt>Putts per round</dt><dd>{p["putts_round"]}</dd></div>'
            f'<div><dt>Three-putts</dt><dd>{p["three_putts"]}</dd></div></dl>\n'
            '        <figure class="exhibit"><figcaption class="exhibit__head"><span class="label">Exhibit 1</span>'
            '<span class="exhibit__title">First putts: make rate against a scratch player</span></figcaption>\n'
            '          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">From</th><th scope="col">Putts</th>'
            '<th scope="col">Made</th><th scope="col">Scratch</th><th scope="col">Gap</th><th scope="col">SG per round</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>\n'
            '          <p class="exhibit__note">Scratch make rates from Arccos’s data. Distances come from GPS, so treat the short buckets as approximate.</p>\n'
            '        </figure>\n'
            '        <figure class="exhibit exhibit--narrow"><figcaption class="exhibit__head"><span class="label">Exhibit 2</span>'
            '<span class="exhibit__title">Lag putting: what the first putt leaves</span></figcaption>\n'
            '          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">First putt from</th><th scope="col">Holes</th>'
            '<th scope="col">Average leave</th><th scope="col">Inside 3 ft</th></tr></thead><tbody>' + lag_rows + '</tbody></table></div>\n'
            '        </figure>\n' + autopsy)


def page_rounds(stats):
    rows = []
    for r in stats['rounds']:
        tot = sum(r['sg'].values())
        d = date.fromisoformat(r['date']).strftime('%b %d, %Y')
        cells = ''.join(f'<td>{sg(r["sg"].get(k, 0))}</td>' for k, _, _ in CATS)
        rows.append(f'<tr><td>{d}</td><td>{r["course"]}</td><td>{r["score"]}{"" if r["holes"] == 18 else " (9)"}</td>'
                    f'<td>{sg(r["score"] - r["par"], 0)}</td>{cells}<td>{sg(tot)}</td></tr>')
    bypar = ''.join(f'<tr><td>Par {p}s</td><td>{sg(v, 1)}</td></tr>' for p, v in stats['scoring']['by_par'].items())
    bylen = ''.join(f'<tr><td>{b} yd</td><td>{sg(v, 1)}</td></tr>'
                    for b, v in sorted(stats['scoring']['par4_by_length'].items()))
    return ('        <figure class="exhibit"><figcaption class="exhibit__head"><span class="label">Exhibit 1</span>'
            '<span class="exhibit__title">Every sensor-tracked round</span></figcaption>\n'
            '          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">Date</th><th scope="col">Course</th>'
            '<th scope="col">Score</th><th scope="col">To par</th><th scope="col">Tee</th><th scope="col">App</th>'
            '<th scope="col">Short</th><th scope="col">Putt</th><th scope="col">Total SG</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>\n        </figure>\n'
            '        <figure class="exhibit exhibit--narrow"><figcaption class="exhibit__head"><span class="label">Exhibit 2</span>'
            '<span class="exhibit__title">Average over par, by hole</span></figcaption>\n'
            '          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">Hole</th><th scope="col">Over par</th></tr></thead><tbody>'
            + bypar + '</tbody></table></div>\n        </figure>\n'
            '        <figure class="exhibit exhibit--narrow"><figcaption class="exhibit__head"><span class="label">Exhibit 3</span>'
            '<span class="exhibit__title">Par 4s by length</span></figcaption>\n'
            '          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">Length</th><th scope="col">Over par</th></tr></thead><tbody>'
            + bylen + '</tbody></table></div>\n'
            '          <p class="exhibit__note">Long par 4s are the hardest holes on any card. The question is whether I lose more there than a scratch player would.</p>\n'
            '        </figure>\n')


def page_practice(stats):
    return ('        <div class="prose">'
            '<p>This page is waiting on its data. I practice on a TrackMan simulator, and each session’s shots, club speed, '
            'ball speed, smash factor, carry and dispersion per club, will land here: a true gapping chart from measured carries, '
            'not guesses, and the spread of each club mapped the same way the approach page maps my on-course misses.</p>'
            '<p>The point of putting practice data next to play data is the loop: if four weeks of wedge work do not move my '
            'proximity from 75–125 yards on the course, the practice was the wrong practice. The site will show both sides.</p>'
            '</div>\n')


SUBPAGES = {
    'golf-driving.html': ('Driving', 'Off the tee: distance, penalties and the misses that cost strokes.', page_driving),
    'golf-approach.html': ('Approach', 'Approach play by distance: strokes gained, proximity and greens hit, against scratch.', page_approach),
    'golf-short-game.html': ('Short game', 'Inside 50 yards: up and down rate and where strokes leak around the green.', page_short),
    'golf-putting.html': ('Putting', 'Make rates by distance against a scratch player, lag putting and the three-putt autopsy.', page_putting),
    'golf-rounds.html': ('Rounds & scoring', 'Every sensor-tracked round, and scoring by hole type and length.', page_rounds),
    'golf-practice.html': ('Practice, measured', 'TrackMan practice sessions: speeds, carries, gapping and dispersion per club.', page_practice),
}


def write_subpages(hub_html, stats):
    head = hub_html[:hub_html.index('<main id="main">')]
    tail = hub_html[hub_html.index('</main>'):]
    for fname, (title, dek, render) in SUBPAGES.items():
        h = head
        h = re.sub(r'<title>.*?</title>', f'<title>{title} · Road to scratch · Jack Raney</title>', h)
        h = re.sub(r'(<meta name="description" content=")[^"]*', r'\g<1>' + dek, h)
        h = re.sub(r'(<link rel="canonical" href=")[^"]*', r'\g<1>https://jackraney.com/' + fname.replace('.html', ''), h)
        h = re.sub(r'(<meta property="og:url" content=")[^"]*', r'\g<1>https://jackraney.com/' + fname.replace('.html', ''), h)
        h = re.sub(r'(<meta property="og:title" content=")[^"]*', r'\g<1>' + title, h)
        h = re.sub(r'(<meta property="og:description" content=")[^"]*', r'\g<1>' + dek, h)
        h += ('<main id="main">\n  <article>\n    <header class="wrap doc-head">\n      <div class="doc-head__inner">\n'
              '        <a class="back" href="golf.html">← Road to scratch</a>\n'
              f'        <h1>{title}</h1>\n        <p class="dek">{dek}</p>\n'
              + golf_nav(fname) +
              '      </div>\n    </header>\n\n    <div class="wrap memo">\n      <div class="stack">\n'
              + render(stats) + source_note(stats) +
              '      </div>\n    </div>\n  </article>\n')
        path = os.path.join(ROOT, fname)
        old = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
        if h + tail != old:
            open(path, 'w', encoding='utf-8').write(h + tail)
            print(fname, 'updated')


if __name__ == '__main__':
    main()
