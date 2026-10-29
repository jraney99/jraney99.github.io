#!/usr/bin/env python3
"""Turn the US Census state outlines into SVG paths the site can draw offline.

Input is us-atlas' states-10m TopoJSON (Census TIGER, public domain), kept in
tools/ so the build never reaches the network. Output is data/us-states.json:
one SVG path per state in the lower 48, projected with an Albers conic equal
area, plus the viewBox they fit. The map page projects its pins with the same
function, so a pin cannot drift from the outline it sits on.

Run again only if the source file is replaced.
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tools', 'states-10m.json')
OUT = os.path.join(ROOT, 'data', 'us-states.json')

# Albers conic equal area. The lower 48 fill the canvas; Hawaii gets its own
# projection and sits in the empty Pacific corner, the way every US map does it.
LON0, PAR1, PAR2 = -96.0, 29.5, 45.5
MIN_PX = 1.2        # smallest gap between kept points, in output pixels
MAIN = {'lon0': -96.0, 'parallels': (29.5, 45.5), 'ref': 37.5}
INSETS = {'Hawaii': {'lon0': -157.0, 'parallels': (8.0, 18.0), 'ref': 20.0,
                     'box': (34, 430, 190, 560),    # x0, y0, x1, y1 on the finished map
                     'label': (34, 420)}}           # where to write its name
DROP = {'Alaska', 'Puerto Rico', 'United States Virgin Islands', 'American Samoa',
        'Guam', 'Commonwealth of the Northern Mariana Islands'}


def albers(lon, lat, spec):
    p1, p2 = math.radians(spec['parallels'][0]), math.radians(spec['parallels'][1])
    n = (math.sin(p1) + math.sin(p2)) / 2
    c = math.cos(p1) ** 2 + 2 * n * math.sin(p1)
    rho0 = math.sqrt(c - 2 * n * math.sin(math.radians(spec['ref']))) / n
    lam = math.radians(lon - spec['lon0']) * n
    rho = math.sqrt(c - 2 * n * math.sin(math.radians(lat))) / n
    return rho * math.sin(lam), rho0 - rho * math.cos(lam)


def decode(topo):
    """TopoJSON arcs are quantised deltas; walk them back to lon/lat."""
    sx, sy = topo['transform']['scale']
    tx, ty = topo['transform']['translate']
    arcs = []
    for arc in topo['arcs']:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def ring(arcs, idx):
    out = []
    for i in idx:
        a = arcs[~i][::-1] if i < 0 else arcs[i]
        out.extend(a[1:] if out else a)
    return out


def main():
    topo = json.load(open(SRC))
    arcs = decode(topo)
    raw = {}
    for geom in topo['objects']['states']['geometries']:
        name = geom['properties']['name']
        if name in DROP:
            continue
        polys = geom['arcs'] if geom['type'] == 'MultiPolygon' else [geom['arcs']]
        rings = [ring(arcs, idx) for poly in polys for idx in poly]
        raw[name] = [r for r in rings if len(r) >= 4]

    out = {'states': {}, 'insets': {}}

    def emit(names, spec, box=None):
        """Project, fit, and write these states as SVG paths. Returns the transform
        so the page can put a pin through exactly the same maths."""
        pts = {n: [[albers(lon, lat, spec) for lon, lat in r] for r in raw[n]] for n in names}
        flat = [p for rings in pts.values() for r in rings for p in r]
        xs = [p[0] for p in flat]
        ys = [p[1] for p in flat]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if box:
            bx0, by0, bx1, by1 = box
            k = min((bx1 - bx0) / (x1 - x0), (by1 - by0) / (y1 - y0))
            dx, dy = bx0, by0
        else:
            k = 960.0 / (x1 - x0)
            dx = dy = 0.0
        place = lambda p: (round((p[0] - x0) * k + dx, 1), round((y1 - p[1]) * k + dy, 1))
        for name, rings in pts.items():
            d = ''
            for r in rings:
                prev, seg = None, []
                for p in r:
                    q = place(p)
                    if prev is None or abs(q[0] - prev[0]) + abs(q[1] - prev[1]) >= MIN_PX:
                        seg.append(q)
                        prev = q
                if len(seg) < 3:
                    continue
                if seg[0] != seg[-1]:
                    seg.append(seg[0])
                d += 'M' + 'L'.join('%g %g' % q for q in seg) + 'Z'
            if d:
                out['states'][name] = d
        return {'lon0': spec['lon0'], 'parallels': list(spec['parallels']), 'ref': spec['ref'],
                'x0': x0, 'y1': y1, 'k': k, 'dx': dx, 'dy': dy}, (x1 - x0) * k, (y1 - y0) * k

    lower48 = [n for n in raw if n not in INSETS]
    out['projection'], w, h = emit(lower48, MAIN)
    out['viewBox'] = '0 0 %g %g' % (round(w, 1), round(h, 1))
    out['labels'] = []
    for name, spec in INSETS.items():
        out['insets'][name], _, _ = emit([name], spec, spec['box'])
        if spec.get('label'):
            out['labels'].append({'text': name, 'x': spec['label'][0], 'y': spec['label'][1]})

    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print('%d states + %d inset(s) -> %s (%.0f KB), viewBox %s'
          % (len(out['states']) - len(INSETS), len(INSETS), os.path.relpath(OUT, ROOT),
             os.path.getsize(OUT) / 1024, out['viewBox']))


if __name__ == '__main__':
    main()
