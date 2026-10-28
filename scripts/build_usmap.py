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

# Albers conic equal area, the standard US parameters
LON0, PAR1, PAR2 = -96.0, 29.5, 45.5
MIN_PX = 1.2        # smallest gap between kept points, in output pixels
SKIP = {'Alaska', 'Hawaii', 'Puerto Rico', 'United States Virgin Islands',
        'American Samoa', 'Guam', 'Commonwealth of the Northern Mariana Islands',
        'District of Columbia'}
KEEP_DC = 'District of Columbia'   # too small to draw, still worth a pin later


def albers(lon, lat):
    p1, p2 = math.radians(PAR1), math.radians(PAR2)
    n = (math.sin(p1) + math.sin(p2)) / 2
    c = math.cos(p1) ** 2 + 2 * n * math.sin(p1)
    rho0 = math.sqrt(c - 2 * n * math.sin(math.radians(37.5))) / n
    lam = math.radians(lon - LON0) * n
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
    states, pts_all = {}, []
    for geom in topo['objects']['states']['geometries']:
        name = geom['properties']['name']
        if name in SKIP and name != KEEP_DC:
            continue
        polys = geom['arcs'] if geom['type'] == 'MultiPolygon' else [geom['arcs']]
        rings = []
        for poly in polys:
            for idx in poly:
                pts = [albers(lon, lat) for lon, lat in ring(arcs, idx)]
                if len(pts) < 4:
                    continue
                rings.append(pts)
                pts_all.extend(pts)
        if rings:
            states[name] = rings

    xs = [p[0] for p in pts_all]
    ys = [p[1] for p in pts_all]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w = 960.0
    k = w / (x1 - x0)
    h = round((y1 - y0) * k, 1)

    def place(p):
        # the conic's y grows northward; SVG's grows downward, so it flips here
        return round((p[0] - x0) * k, 1), round((y1 - p[1]) * k, 1)

    out = {'viewBox': '0 0 %g %g' % (w, h), 'projection': {
        'lon0': LON0, 'parallels': [PAR1, PAR2], 'x0': x0, 'y1': y1, 'k': k},
        'states': {}}
    for name, rings in states.items():
        d = ''
        for pts in rings:
            # The source is 1:10m detail; this map is 960px wide, so points closer
            # together than MIN_PX cannot be told apart. Dropping them cuts the file
            # by about two thirds with no visible change to the outline.
            prev, seg = None, []
            for p in pts:
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
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print('%d states -> %s (%.0f KB), viewBox %s'
          % (len(out['states']), os.path.relpath(OUT, ROOT),
             os.path.getsize(OUT) / 1024, out['viewBox']))


if __name__ == '__main__':
    main()
