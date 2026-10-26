"""Render the data on golf.html from data/golf.json (written daily by Archibald's ghin-handicap skill).

Run from the repo root: python3 scripts/build_golf.py
Only the region between the golf:start and golf:end markers is rewritten.
"""
import json
import math
import os
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


def body(g):
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
    t = g.get('tracked') or {}
    bits = []
    if t.get('fairways', [0, 0])[1] >= 30:
        bits.append(f'fairways hit {t["fairways"][0] / t["fairways"][1]:.0%} ({t["fairways"][1]} holes)')
    if t.get('greens', [0, 0])[1] >= 30:
        bits.append(f'greens in regulation {t["greens"][0] / t["greens"][1]:.0%} ({t["greens"][1]} holes)')
    if t.get('putts', [0, 0])[1] >= 30:
        bits.append(f'{t["putts"][0] / t["putts"][1]:.2f} putts per hole ({t["putts"][1]} holes)')
    if bits:
        out.append(f'        <div class="prose"><p>On the holes where I also tracked stats: {", ".join(bits)}.</p></div>\n')
    a = g.get('arccos') or {}
    cats = a.get('categories') or {}
    if cats:
        rows = ''.join(f'<tr><td>{k}</td><td>{"+" if v > 0 else ("−" if v < 0 else "")}{abs(v):.1f}</td></tr>' for k, v in cats.items())
        out.append('        <figure class="exhibit exhibit--narrow"><figcaption class="exhibit__head"><span class="label">Exhibit 3</span>'
                   '<span class="exhibit__title">Strokes gained per round, from Arccos</span></figcaption>\n'
                   '          <div class="table-wrap"><table class="data"><thead><tr><th scope="col">Part of the game</th>'
                   '<th scope="col">Strokes gained</th></tr></thead><tbody>' + rows + '</tbody></table></div>\n'
                   f'          <p class="exhibit__note">From {a.get("rounds")} rounds tracked with Arccos sensors, compared with a '
                   'scratch golfer. Negative means strokes lost.</p>\n        </figure>\n')
    else:
        out.append('        <div class="prose"><p>Strokes gained, which shows exactly where shots are lost off the tee, on approach, '
                   'around the green and on the greens, will appear here once enough rounds are tracked with Arccos.</p></div>\n')
    practice = []
    if g.get('courses_played'):
        practice.append(f'I’ve played {g["courses_played"]} different courses')
    p = g.get('putting') or {}
    if p.get('nights') and p.get('since'):
        s = date.fromisoformat(p['since'])
        line = f'logged {p["nights"]} nights of putting practice since {s.strftime("%B")} {s.day}'
        if p.get('goal'):
            line += f' (goal: {p["goal"]} putts a night)'
        if (p.get('streak') or 0) >= 3:
            line += f', with a current streak of {p["streak"]} nights'
        practice.append(line)
    if practice:
        out.append('        <div class="prose"><h2>Practice and play</h2><p>' + ', and I’ve '.join(practice) + '.</p></div>\n')
    out.append(f'        <p class="note">From my GHIN record: every Handicap Index revision and every posted score. '
               f'Course names are left out. Updated daily; last checked {date.fromisoformat(today).strftime("%B")} '
               f'{date.fromisoformat(today).day}, {today[:4]}.</p>\n')
    return ''.join(out)


def main():
    path = os.path.join(ROOT, 'data', 'golf.json')
    if not os.path.exists(path) or not os.path.exists(PAGE):
        print('no data/golf.json or golf.html; nothing to do')
        return
    page = open(PAGE, encoding='utf-8').read()
    a, b = page.index(START) + len(START), page.index(END)
    new = page[:a] + '\n' + body(json.load(open(path, encoding='utf-8'))) + '        ' + page[b:]
    if new != page:
        open(PAGE, 'w', encoding='utf-8').write(new)
        print('golf.html updated')
    else:
        print('golf.html unchanged')


if __name__ == '__main__':
    main()
