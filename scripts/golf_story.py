"""What each golf page's numbers say, worked out from the data on every build.

Jack, 2026-11-02: "I want the data to tell the story and explain why I am getting the numbers
that I am." Each page opens with a few beats: a short claim carrying its number, then the
evidence behind it. Every figure is read from golf.json, golf-stats.json or trackman.json when
the page is built, so a beat cannot go stale the way the hand-written "initial read" did.

Beats describe what happened and never say how to swing; what to change belongs to his coach.
A beat whose data is missing is left out rather than guessed. A beat is (lead, detail), both
already HTML-safe.
"""
import re
from collections import Counter
from datetime import date, timedelta
from html import escape

NAMES = {'driving': 'driving', 'approach': 'approach', 'short': 'short game', 'putting': 'putting'}
# The bag, longest first: how gaps are read down it. build_golf's sample table uses the same order.
BAG_ORDER = ('Dr', '3w', '2i', '4i', '5i', '6i', '7i', '8i', '9i', 'Pw', '50\u00b0', '54\u00b0', '58\u00b0')
CLUB_NAMES = {'Dr': 'Driver', '3w': '3-wood', '5w': '5-wood', '2i': '2-iron', '3i': '3-iron',
              '4i': '4-iron', '5i': '5-iron', '6i': '6-iron', '7i': '7-iron', '8i': '8-iron',
              '9i': '9-iron', 'Pw': 'Pitching wedge'}


# ---------------------------------------------------------------------------
# wording
# ---------------------------------------------------------------------------

def day(iso):
    d = date.fromisoformat(str(iso)[:10])
    return d.strftime('%b ') + str(d.day)


def and_join(xs):
    xs = list(xs)
    if not xs:
        return ''
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]


def signed(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.1f}'


def costs(v):
    """Strokes gained per round, in words: 'costs 1.5 strokes' or 'gains 0.4 strokes'."""
    return f'costs {abs(v):.1f} strokes' if v < 0 else f'gains {v:.1f} strokes' if v > 0 else 'breaks even'


def lost_or_gained(v):
    return f'lost {abs(v):.1f}' if v < 0 else f'gained {v:.1f}' if v > 0 else 'broke even'


def an(score):
    return ('an ' if 80 <= score < 90 or score in (8, 11, 18) else 'a ') + f'{score:.0f}'


def index_number(text):
    """GHIN writes a plus handicap as '+0.6', which is below scratch."""
    return -float(text[1:]) if str(text).startswith('+') else float(text)


def ci_text(ci):
    return f'{signed(ci[0])} to {signed(ci[1])}'


def settled(ci):
    if not ci:
        return 'There is no uncertainty range for this yet.'
    if ci[1] < 0:
        return f'The range, {ci_text(ci)} a round, is all below zero, so in this sample the loss is real.'
    if ci[0] > 0:
        return f'The range, {ci_text(ci)} a round, is all above zero.'
    return f'The range, {ci_text(ci)} a round, still includes zero, so it is not settled.'


def club_name(key):
    return CLUB_NAMES.get(key, key)


def band_edges(key):
    """'75-100' -> (75, 100); '200+' -> (200, None); '<350' -> (None, 350); '>420' -> (420, None)."""
    k = str(key).replace('–', '-')
    if k.endswith('+'):
        return float(k[:-1]), None
    if k.startswith('<'):
        return None, float(k[1:])
    if k.startswith('>'):
        return float(k[1:]), None
    lo, hi = k.split('-')
    return float(lo), float(hi)


def band_label(key):
    lo, hi = band_edges(key)
    if lo is None:
        return f'under {hi:g}'
    if hi is None:
        return f'{lo:g}+'
    return f'{lo:g}–{hi:g}'


def outer_span(keys, others, unit):
    """One range from the lowest to the highest of `keys` when none of `others` sits inside it, so
    a thin band in the middle does not break '0 to 15 ft' into a list."""
    edges = [band_edges(k) for k in keys]
    lo, hi = min(e[0] or 0 for e in edges), max(e[1] if e[1] is not None else float('inf') for e in edges)
    inside = any(lo <= (band_edges(k)[0] or 0) < hi for k in others)
    if inside or hi == float('inf'):
        return span(keys, unit)
    return f'{lo:g} to {hi:g} {unit}'


def span(keys, unit):
    """Touching bands as one range ('75 to 150 yd'); bands with a hole between them are listed."""
    keys = sorted(keys, key=lambda k: band_edges(k)[0] if band_edges(k)[0] is not None else -1)
    edges = [band_edges(k) for k in keys]
    touching = all(a[1] is not None and a[1] == b[0] for a, b in zip(edges, edges[1:]))
    if touching and edges[0][0] is not None:
        hi = edges[-1][1]
        return f'{edges[0][0]:g} to {hi:g} {unit}' if hi is not None else f'{edges[0][0]:g} {unit} and out'
    return and_join(band_label(k) for k in keys) + f' {unit}'


# ---------------------------------------------------------------------------
# what the rounds hold
# ---------------------------------------------------------------------------

def holes(stats):
    return [h for r in stats.get('rounds') or [] for h in r.get('card') or []
            if isinstance(h.get('score'), (int, float)) and isinstance(h.get('par'), (int, float))]


def rounds18(stats):
    return [r for r in stats.get('rounds') or [] if r.get('holes') == 18 and r.get('sg')]


def months(stats):
    ds = sorted(r['date'] for r in stats.get('rounds') or [])
    if not ds:
        return ''
    a, b = date.fromisoformat(ds[0]), date.fromisoformat(ds[-1])
    if (a.year, a.month) == (b.year, b.month):
        return a.strftime('%b %Y')
    return (f'{a:%b} to {b:%b %Y}' if a.year == b.year else f'{a:%b %Y} to {b:%b %Y}')


def per_round(stats, key):
    return (stats.get('sg') or {}).get('per_round', {}).get(key)


def ci_of(stats, key):
    return ((stats.get('sg') or {}).get('ci') or {}).get(key)


def opening(stats, key):
    """The first beat on every part's page: what it costs a round, and whether that is settled."""
    v = per_round(stats, key)
    if v is None:
        return None
    pr = (stats.get('sg') or {}).get('per_round') or {}
    worst = min(pr, key=pr.get) == key and v < 0
    lead = f'{NAMES[key].capitalize()} {costs(v)} a round' + (', the most of any part.' if worst else '.')
    return lead, settled(ci_of(stats, key))


def index_beat(g):
    revs = g.get('revisions') or []
    if not revs:
        return None
    now = revs[-1]
    i = len(revs) - 1
    while i > 0 and revs[i - 1]['index'] == now['index']:
        i -= 1
    rule = ('The index averages my best 8 of my latest 20 score differentials, so a round well under '
            'it pulls it down and one well over it usually does not count at all.')
    if i == 0:
        return f'Index {escape(str(now["index"]))}.', f'Unchanged since {day(revs[0]["date"])}. {rule}'
    changed = revs[i]
    move = index_number(now['index']) - index_number(revs[i - 1]['index'])
    lead = (f'Index {escape(str(now["index"]))}, {"down" if move < 0 else "up"} {abs(move):.1f} '
            f'on {day(changed["date"])}.')
    week = (date.fromisoformat(changed['date']) - timedelta(days=7)).isoformat()
    before = sorted((r for r in g.get('recent_rounds') or []
                     if r.get('score') and r.get('differential') is not None
                     and week <= r['date'] <= changed['date']),
                    key=lambda r: r['date'], reverse=True)[:2]
    if not before:
        return lead, rule
    said = and_join(f'{an(r["score"])} on {day(r["date"])} (differential {r["differential"]:.1f})'
                    for r in before)
    return lead, f'The rounds just before it: {said}. {rule}'


def gap_beat(stats):
    pr = (stats.get('sg') or {}).get('per_round') or {}
    total = (stats.get('sg') or {}).get('total')
    if total is None or not pr:
        return None
    order = sorted((k for k in NAMES if pr.get(k) is not None), key=lambda k: pr[k])
    losing = [f'{NAMES[k]} {abs(pr[k]):.1f}' for k in order if pr[k] < 0]
    gaining = [f'{NAMES[k]} gains {pr[k]:.1f}' for k in order if pr[k] > 0]
    newest = max(r['date'] for r in stats['rounds'])
    detail = (f'Across {stats["rounds_n"]} rounds with every shot recorded ({months(stats)}), '
              f'the loss splits {and_join(losing)}' + (f'; {and_join(gaining)}' if gaining else '') + '. '
              f'The newest of those rounds is from {day(newest)}; rounds posted since count for the index '
              'but carry no shot data.')
    return f'{abs(total):.1f} strokes a round from scratch.', detail


def doubles_beat(stats):
    hs = holes(stats)
    if not hs:
        return None
    over = sum(h['score'] - h['par'] for h in hs)
    dbl = [h for h in hs if h['score'] - h['par'] >= 2]
    if not dbl or over <= 0:
        return None
    made = sum(h['score'] - h['par'] for h in dbl)
    pen = sum(1 for h in dbl if h.get('pen'))
    missed = sum(1 for h in dbl if h.get('gir') is False)
    three = sum(1 for h in dbl if (h.get('putts') or 0) >= 3)
    parts = [f'a penalty stroke was on {pen}', f'{missed} missed the green', f'{three} had a three-putt']
    lead = f'{len(dbl)} doubles or worse made {made} of my {over} strokes over par.'
    detail = (f'They are {len(dbl) / len(hs):.0%} of {len(hs)} holes. Of the {len(dbl)}, '
              f'{and_join(parts)}.')
    return lead, detail


def swing_beat(stats, only=None):
    """The part that varies most between 18-hole rounds. `only` keeps it to one part's page."""
    rs = rounds18(stats)
    if len(rs) < 3:
        return None
    spread = {k: max(r['sg'].get(k, 0) for r in rs) - min(r['sg'].get(k, 0) for r in rs) for k in NAMES}
    k = max(spread, key=spread.get)
    if only and k != only:
        return None
    high = sorted(rs, key=lambda r: -r['score'])[:2]
    low = min(rs, key=lambda r: r['score'])
    said = and_join([f'{lost_or_gained(r["sg"].get(k, 0))} in the {r["score"]}' for r in high]
                    + [f'{lost_or_gained(low["sg"].get(k, 0))} in the {low["score"]}, my lowest'])
    second = sorted(spread.values())[-2]
    return (f'The {NAMES[k]} swings the most from round to round.',
            f'It {said}. No other part varied by more than {second:.1f} strokes across these rounds.')


def scramble(stats):
    missed = [h for h in holes(stats) if h.get('gir') is False]
    return missed, [h for h in missed if h['score'] <= h['par']]


# ---------------------------------------------------------------------------
# the pages
# ---------------------------------------------------------------------------

def overview(stats, g):
    return [b for b in (index_beat(g), gap_beat(stats), doubles_beat(stats), swing_beat(stats)) if b]


def driving(stats, tm=None):
    d = stats.get('driving') or {}
    out = [opening(stats, 'driving')]
    v = per_round(stats, 'driving')
    leak = next((l for l in stats.get('leaks') or [] if 'penalt' in l['name'].lower()), None)
    pens, tees = d.get('tee_penalties'), d.get('tee_shots')
    if leak and pens and tees and stats.get('holes'):
        each = abs(leak['per_round']) / (pens / (stats['holes'] / 18))
        detail = (f'One tee shot in {round(tees / pens)} took a penalty, and each cost about {each:.1f} '
                  'strokes against a clean tee shot.')
        clean = (v or 0) - leak['per_round']
        if v is not None and clean > 0:
            detail += (f' The clean ones gained about {clean:.1f} a round on scratch, so the penalties are '
                       'more than the whole loss.')
        out.append((f'Penalties: {pens} in {tees} tee shots, about {abs(leak["per_round"]):.1f} strokes a round.',
                    detail))
    td = d.get('tee_decision') or {}
    clubs = td.get('clubs') or []
    dr = next((c for c in clubs if c['club'] == 'Driver'), None)
    other = next((c for c in clubs if c['club'] != 'Driver'), None)
    if dr and other:
        verdict = td.get('verdict') or {}
        gap = dr['sg_per_shot'] - other['sg_per_shot']
        detail = (f'The driver took a penalty {dr["penalty_rate"]}% of the time, the {escape(other["club"])} '
                  f'{other["penalty_rate"]}%')
        detail += (f', and the driver finished {verdict["yards"]} yd farther on median. ' if verdict.get('yards')
                   else '. ')
        detail += (f'Per tee shot the driver was {abs(gap):.2f} strokes {"better" if gap > 0 else "worse"}'
                   + ('.' if verdict.get('callable') else ', a gap this sample cannot yet call.'))
        out.append((f'Driver on {dr["shots"]} tee shots, {escape(other["club"])} on {other["shots"]}.', detail))
    form = driver_form(tm)
    if d.get('driver_median_yd'):
        lead = f'Driver: {d["driver_median_yd"]} yd on the course' + (
            f', {form["carry"]:.0f} yd carry in practice.' if form else '.')
        detail = (f'{d["driver_median_yd"]} is start to rest across {d.get("driver_measured", "the")} measured '
                  'drives, so it includes roll.')
        if form:
            detail += (f' {form["carry"]:.0f} is carry before roll: the median of my last {form["n"]} drives '
                       'on TrackMan.')
        out.append((lead, detail))
    return [b for b in out if b]


def approach_bands(stats):
    """(losing band keys, their total, the other well-sampled keys, their total)."""
    b = (stats.get('approach') or {}).get('buckets') or {}
    losing = [k for k, v in b.items() if not v.get('thin') and v.get('ci') and v['ci'][1] < 0]
    rest = [k for k, v in b.items() if not v.get('thin') and k not in losing]
    return (losing, sum(b[k]['sg_round'] for k in losing), rest, sum(b[k]['sg_round'] for k in rest))


def approach_band_beat(stats):
    losing, lost_sum, rest, rest_sum = approach_bands(stats)
    if not losing:
        return ('No distance band clearly loses on its own.',
                'Every band with enough shots still has a range that includes zero.')
    lead = f'The loss sits at {span(losing, "yd")}.'
    detail = (f'{"Those bands lose" if len(losing) > 1 else "That band loses"} {abs(lost_sum):.1f} a round'
              + (' between them' if len(losing) > 1 else '') + ', each with its whole range below zero.')
    if rest:
        detail += f' The other {len(rest)} band{"s" if len(rest) > 1 else ""} with enough shots net {signed(rest_sum)}.'
    return lead, detail


def approach(stats):
    a = stats.get('approach') or {}
    out = [opening(stats, 'approach'), approach_band_beat(stats)]
    m = {k: v for k, v in (a.get('miss_dir') or {}).items() if v}
    total = sum(m.values())
    if total:
        top = max(m, key=m.get)
        rest = ', '.join(f'{k} {m[k]}' for k in sorted(m, key=m.get, reverse=True) if k != top)
        out.append((f'{m[top]} of {total} approach misses finish {top}.',
                    f'That is {m[top] / total:.0%}. The rest: {rest}.'))
    if a.get('gir_pct') is not None:
        missed, saved = scramble(stats)
        detail = (f'When I hit one, the median ball is {a.get("prox_gir_ft")} ft from the hole; '
                  f'{a.get("prox_all_ft")} ft counting the misses.')
        if missed:
            detail += (f' The {len(missed)} greens I missed went to the short game, which saved par on '
                       f'{len(saved)} of them.')
        out.append((f'Greens hit: {a["gir_pct"]}%.', detail))
    return [b for b in out if b]


def short_game(stats, tour=None):
    s = stats.get('short') or {}
    out = [opening(stats, 'short')]
    b = s.get('buckets') or {}
    if b:
        rows = and_join(f'{band_label(k)} yd {signed(v["sg_round"])} ({v["shots"]} shots)' for k, v in b.items())
        every = all(v['sg_round'] < 0 for v in b.values())
        out.append(('Every distance band loses.' if every else 'By distance:', f'{rows}, per round.'))
    gs = s.get('updown_greenside') or s.get('updown') or {}
    pitch = s.get('updown_pitch') or {}
    if gs.get('of'):
        lead = f'Up and down: {gs["made"]} of {gs["of"]} inside 30 yd' + (
            f', {pitch["made"]} of {pitch["of"]} from 30 to 50.' if pitch.get('of') else '.')
        missed, saved = scramble(stats)
        detail = f'That is {gs["made"] / gs["of"]:.0%} inside 30 yd.'
        scr = ((tour or {}).get('on_course') or {}).get('stats', {}).get('scrambling_pct')
        if missed:
            detail += (f' Counting every missed green, I saved par {len(saved)} times in {len(missed)} '
                       f'({len(saved) / len(missed):.0%})' + (f'; the PGA Tour average is {scr:.0f}%.' if scr else '.'))
        out.append((lead, detail))
    out.append(swing_beat(stats, only='short'))
    return [b for b in out if b]


def putting(stats):
    p = stats.get('putting') or {}
    out = [opening(stats, 'putting')]
    if p.get('putts_round') is not None:
        out.append((f'{p["putts_round"]:.0f} putts a round.',
                    'The count also depends on how many greens I hit and where first putts start, so it is '
                    'not a pure putting number.'))
    if p.get('three_putts'):
        out.append((f'{p["three_putts"]} three-putts, after long first putts.',
                    f'Their first putts started {p["three_putt_first_ft"]} ft away on average; on holes I '
                    f'two-putted, {p["two_putt_first_ft"]} ft. Only the first putt is measured, so the data '
                    'cannot say whether the lag or the next putt was the miss.'))
    b = {k: v for k, v in (p.get('buckets') or {}).items()
         if not v.get('thin') and v.get('scratch_pct') is not None and v.get('made_pct') is not None}
    above = [k for k, v in b.items() if v['made_pct'] - v['scratch_pct'] >= 5]
    below = [k for k, v in b.items() if v['scratch_pct'] - v['made_pct'] >= 5]
    if above or below:
        parts = []
        if above:
            parts.append(f'more than the scratch reference from {outer_span(above, below, "ft")}')
        if below:
            parts.append(f'{"fewer" if above else "fewer than the scratch reference"} from '
                         f'{outer_span(below, above, "ft")}')
        shown = sorted(above + below, key=lambda k: -abs(b[k]['made_pct'] - b[k]['scratch_pct']))[:4]
        rows = '; '.join(f'{band_label(k)} ft, {b[k]["made_pct"]}% against {b[k]["scratch_pct"]}%' for k in shown)
        out.append((f'I hole {" and ".join(parts)}.',
                    f'{rows}. The reference has no traceable distance-matched source yet, so these gaps are provisional.'))
    return [b for b in out if b]


def rounds(stats, g):
    rs = rounds18(stats)
    if not rs:
        return []
    out = []
    low, high = min(rs, key=lambda r: r['score']), max(rs, key=lambda r: r['score'])
    nine = [r for r in stats.get('rounds') or [] if r.get('holes') == 9]
    newest = max(r['date'] for r in stats['rounds'])
    out.append((f'{len(rs)} tracked 18-hole rounds, from {low["score"]} to {high["score"]}.',
                f'Raw strokes with every shot recorded, {months(stats)}'
                + (f', plus {an(nine[0]["score"])} for nine' if nine else '') + '. '
                f'The newest is from {day(newest)}; rounds posted since count for the index but have no shot data.'))
    if low is not high:
        diff = {k: low['sg'].get(k, 0) - high['sg'].get(k, 0) for k in NAMES}
        k = max(diff, key=diff.get)
        if diff[k] > 0:
            others = sum(v for kk, v in diff.items() if kk != k)
            out.append((f'The {NAMES[k]} is most of the gap between my best and worst 18.',
                        f'{low["score"]} at {escape(low["course"])} and {high["score"]} at {escape(high["course"])}: '
                        f'the {NAMES[k]} {lost_or_gained(low["sg"].get(k, 0))} in the {low["score"]} and '
                        f'{lost_or_gained(high["sg"].get(k, 0))} in the {high["score"]}. The other three parts net '
                        f'{abs(others):.1f} between the two rounds.'))
    pl = (stats.get('scoring') or {}).get('par4_by_length') or {}
    if pl:
        worst = max(pl, key=pl.get)
        words = {'<': 'under ', '>': 'over '}
        name = lambda b: words.get(b[0], '') + b.lstrip('<>').replace('-', '–') + ' yd'
        # Over par, so positive is worse: the opposite sign sense to strokes gained.
        over = lambda v: ('+' if v >= 0 else '−') + f'{abs(v):.1f}'
        rest = '; '.join(f'{name(b)} {over(v)}' for b, v in sorted(pl.items(), key=lambda kv: -kv[1]) if b != worst)
        byp = (stats.get('scoring') or {}).get('by_par') or {}
        tail = (' By par: ' + ', '.join(f'{p}s {over(v)}' for p, v in sorted(byp.items())) + ' a hole.') if byp else ''
        out.append((f'Par 4s {name(worst)} average {over(pl[worst])} over par a hole.', f'{rest}.{tail}'))
    return out


def courses(d):
    cs = (d or {}).get('courses') or []
    if not cs:
        return []
    states = Counter(c['state'] for c in cs if c.get('state'))
    ranked = sum(1 for c in cs if c.get('rank') or c.get('state_rank'))
    out = []
    detail = f'{ranked} are ranked by Golf Digest.'
    if states:
        top, n = states.most_common(1)[0]
        detail += f' The most are in {escape(top)} ({n}).'
    most = max(cs, key=lambda c: c.get('times') or 1)
    if (most.get('times') or 1) > 1:
        detail += f' Played most: {escape(most["name"])}, {most["times"]} times.'
    out.append((f'{len(cs)} courses in {len(states)} states.', detail))
    return out


# ---------------------------------------------------------------------------
# TrackMan
# ---------------------------------------------------------------------------

def driver_form(tm, min_shots=8):
    """The driver's current carry: the median of the last 20 drives in any session (trackman.json
    `driver`). Road to 315 heads with this one (Jack, 2026-11-02): a single session's median moved
    298, 287, 293 on 9 to 11 drives."""
    d = (tm or {}).get('driver') or {}
    return d if isinstance(d.get('carry'), (int, float)) and (d.get('n') or 0) >= min_shots else None


def latest_driver(tm, min_shots=8):
    """The latest TrackMan session with enough drives to read, as Road to 315 reads it."""
    for s in sorted((tm or {}).get('session_stats') or [], key=lambda s: str(s.get('date')), reverse=True):
        c = next((c for c in s.get('clubs') or [] if c.get('club') == 'Dr'), None)
        if c and c.get('carry') and (c.get('n') or 0) >= min_shots:
            return dict(c, date=s['date'])
    return None


def trackman(tm, tour=None, bag_order=BAG_ORDER, today=None):
    tm = tm or {}
    today = today or date.today()
    out = []
    if tm.get('sessions_30d') is not None:
        cutoff = (today - timedelta(days=30)).isoformat()
        drills = [s['drill'] for s in tm.get('sessions') or [] if isinstance(s.get('drill'), dict)
                  and str(s.get('date')) >= cutoff and s['drill'].get('balls')]
        detail = ''
        if drills:
            name = escape(drills[0].get('name') or 'the drill')
            detail = (f'{sum(d["balls"] for d in drills)} of them were drill swings: {name}. They count as '
                      'balls hit and never as a yardage.')
        out.append((f'{tm["sessions_30d"]} sessions and {tm.get("balls_30d", 0)} balls in the last 30 days.',
                    detail or 'Every ball counts toward practice volume.'))
    clubs = [c for c in tm.get('clubs') or [] if c.get('carry')]
    if clubs:
        lasts = sorted(str(c['last']) for c in clubs if c.get('last'))
        when = (f', last measured between {day(lasts[0])} and {day(lasts[-1])}' if lasts and lasts[0] != lasts[-1]
                else f', last measured {day(lasts[0])}' if lasts else '')
        out.append((f'{len(clubs)} clubs measured.',
                    'Each yardage is the median of up to that club’s latest 20 swings on a measuring '
                    f'day{when}. Practice-night swings never change them.'))
        rank = {k: i for i, k in enumerate(bag_order)}
        seq = sorted(clubs, key=lambda c: (rank.get(c['club'], 99), -c['carry']))
        gaps = [(a['club'], b['club'], round(a['carry'] - b['carry'])) for a, b in zip(seq, seq[1:])]
        if gaps:
            tight, wide = min(gaps, key=lambda x: x[2]), max(gaps, key=lambda x: x[2])
            detail = (f'Tightest: {club_name(tight[0])} to {club_name(tight[1])}, {tight[2]} yd. '
                      f'Widest: {club_name(wide[0])} to {club_name(wide[1])}, {wide[2]} yd.')
            overlap = [x for x in gaps if x[2] <= 0]
            if overlap:
                a, b, gap = overlap[0]
                detail += f' The {club_name(b)} carries {abs(gap)} yd past the {club_name(a)}.'
            out.append((f'Gaps between clubs run {tight[2]} to {wide[2]} yd.', detail))
        dr = next((c for c in clubs if c['club'] == 'Dr'), None)
        pga = (((tour or {}).get('metrics') or {}))
        mark = lambda m: ((pga.get(m) or {}).get('pga') or {}).get('clubs', {}).get('Dr')
        bs, carry, launch, spin = mark('Ball Speed'), mark('Carry'), mark('Launch Angle'), mark('Spin Rate')
        if dr and dr.get('ball_speed') and bs and carry:
            same = abs(dr['ball_speed'] - bs) < 1.5
            lead = (f'Driver ball speed {dr["ball_speed"]:.0f} mph, '
                    + ('the same as the PGA Tour average.' if same else f'against a PGA Tour average of {bs:.0f}.'))
            detail = f'On a measuring day my driver carried {dr["carry"]:.0f} yd against their {carry:.0f}'
            if dr.get('launch') is not None and launch is not None and dr.get('spin') and spin:
                detail += (f', launching at {dr["launch"]:.1f}° against {launch:.1f}° with '
                           f'{dr["spin"]:,.0f} rpm against {spin:,.0f}')
            out.append((lead, detail + '. Carry comes from ball speed, launch and spin together.'))
        sides = sorted((c for c in clubs if c.get('side_spread') is not None), key=lambda c: -c['side_spread'])
        if len(sides) >= 4:
            top, rest = sides[:3], sides[3:]
            next_two = and_join('%s ±%.0f' % (club_name(c['club']).lower(), c['side_spread']) for c in top[1:])
            out.append((f'{club_name(top[0]["club"])} spreads widest: ±{top[0]["side_spread"]:.0f} yd left to right.',
                        f'Then {next_two}; the other {len(rest)} stay within '
                        f'±{max(c["side_spread"] for c in rest):.0f} yd.'))
    return out


# ---------------------------------------------------------------------------
# practice grades, in words
# ---------------------------------------------------------------------------

def grade_lines(grade):
    """What a session was checked on and how it did, one plain line per check (Jack, 2026-11-02:
    "missed all 2" did not say what was missed). Reads the grader's own results; a grade written
    before results existed is shown as its summary."""
    if not isinstance(grade, dict):
        return [str(grade)] if grade else []
    lines = []
    for r in grade.get('results') or []:
        what, measured, target, n = r.get('what') or 'Check', str(r.get('measured') or ''), r.get('target'), r.get('n')
        inside = re.match(r'(\d+)% inside (.+)$', measured)
        if inside and n:
            pct = int(inside.group(1))
            said = f'{what}: {round(pct * n / 100)} of {n} inside {inside.group(2)} ({pct}%)'
        else:
            said = f'{what}: {measured}' + (f', {n} shots' if n else '')
        if target:
            said += f'; needs {target}'
        lines.append(said + ('. Met.' if r.get('pass') else '. Not met.'))
    if not lines:
        lines.append('Nothing graded: no part of this session has a target the export can check.'
                     if grade.get('ungraded') else (grade.get('summary') or 'Not graded.'))
    return lines


def grade_tally(grade):
    """'1 of 2 met'; 'not graded' when the grader looked and nothing had a checkable target; an older
    grade that kept only its summary is shown as that summary."""
    if not isinstance(grade, dict):
        return str(grade) if grade else '\u2014'
    results = grade.get('results')
    if results:
        return f'{sum(1 for r in results if r.get("pass"))} of {len(results)} met'
    return 'not graded' if 'results' in grade else (grade.get('summary') or '\u2014')
