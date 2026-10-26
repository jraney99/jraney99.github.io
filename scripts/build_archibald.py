"""Draw the "jobs created" step chart on index.html and archibald.html from data/archibald.json
(written daily by Archibald's site-facts skill). Only the jobs-chart markers' contents change."""
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START, END = '<!-- jobs-chart:start -->', '<!-- jobs-chart:end -->'


def paths(days, today):
    first, last = date.fromisoformat(days[0]), date.fromisoformat(today)
    span = max((last - first).days, 1)
    total = len(days)
    X = lambda d: (d - first).days / span * 1000
    Y = lambda n: 1000 - n / total * 930
    pts, n = [], 0
    for d in sorted(set(days)):
        x = X(date.fromisoformat(d))
        pts.append(f'L{x:.1f} {Y(n):.1f}')
        n += days.count(d)
        pts.append(f'L{x:.1f} {Y(n):.1f}')
    pts.append(f'L1000 {Y(n):.1f}')
    line = f'M0 {Y(0):.1f} ' + ' '.join(pts)
    return (f'<path class="area" d="{line} L1000 1000 L0 1000 Z"/>'
            f'<path class="line" vector-effect="non-scaling-stroke" d="{line}"/>')


def main():
    path = os.path.join(ROOT, 'data', 'archibald.json')
    if not os.path.exists(path):
        print('no data/archibald.json; charts unchanged')
        return
    data = json.load(open(path, encoding='utf-8'))
    svg = paths(sorted(data['created']), data['counted'])
    for name in ('index.html', 'archibald.html'):
        p = os.path.join(ROOT, name)
        page = open(p, encoding='utf-8').read()
        if START not in page:
            continue
        a, b = page.index(START) + len(START), page.index(END)
        new = page[:a] + svg + page[b:]
        if new != page:
            open(p, 'w', encoding='utf-8').write(new)
            print(f'{name} chart updated')


if __name__ == '__main__':
    main()
