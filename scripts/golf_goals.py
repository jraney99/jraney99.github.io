"""Shared golf goal presentation. Editorial analysis stays dated; measurements update.

Goals are registered once in data/golf-goals.json with an owning page and stable
anchor. The overview lists them; the owning page holds the full experiment and
history. TrackMan club goals use per-session summaries, never preview values or
rolling aggregates misrepresented as individual sessions.
"""
import json
import math
from datetime import date
from html import escape
from pathlib import Path


def esc(value):
    return escape(str(value), quote=True)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def fmt(value, unit=''):
    if not number(value):
        return '—'
    text = f'{value:,.1f}'.rstrip('0').rstrip('.')
    return text + (unit if unit in ('°', '%') else (' ' + unit if unit else ''))


def load_goals(root):
    path = Path(root) / 'data' / 'golf-goals.json'
    if not path.exists():
        return []
    goals = json.loads(path.read_text())['goals']
    ids = [g['id'] for g in goals]
    if len(ids) != len(set(ids)):
        raise ValueError('Golf goals need unique anchors')
    return goals


def observations(goal, tm):
    if goal['source'] != 'trackman':
        raise ValueError('Unsupported goal source: ' + goal['source'])
    out = []
    for session in (tm or {}).get('session_stats', []):
        day = session.get('date') or ''
        try:
            date.fromisoformat(day)
        except ValueError:
            continue
        if day < goal['started']:
            continue
        club = next((c for c in session.get('clubs', []) if c.get('club') == goal['club']), None)
        if club and number(club.get(goal['metric'])):
            out.append(dict(club, date=day, session_id=session.get('id', '')))
    return sorted(out, key=lambda r: (r['date'], r['session_id']))


def eligible(goal, rows):
    return [r for r in rows if r.get('n', 0) >= goal.get('min_shots', 8)]


def state(goal, rows):
    good = eligible(goal, rows)
    if not good:
        return 'Awaiting a baseline'
    now = good[-1][goal['metric']]
    reached = now >= goal['target'] if goal['direction'] == 'higher' else now <= goal['target']
    if reached:
        return 'Target met this session'
    return 'Baseline recorded' if len(good) == 1 else 'Tracking progress'


def goal_link(goal):
    return esc(goal['page'] + '#' + goal['id'])


def index(goals, tm):
    active = [g for g in goals if g['status'] == 'active']
    if not active:
        return ''
    cards = []
    for g in active:
        rows = observations(g, tm)
        good = eligible(g, rows)
        current = fmt(good[-1][g['metric']], g['unit']) if good else 'Awaiting data'
        cards.append(f'<a class="goal-index-card" href="{goal_link(g)}">'
                     f'<span class="lbl">{esc(g["category"])} · {esc(state(g, rows))}</span>'
                     f'<h3>{esc(g["title"])}</h3><p>{esc(g["description"])}</p>'
                     f'<span class="goal-index-number">{current} <small>→ {fmt(g["target"], g["unit"])}</small></span>'
                     f'<span class="goal-index-label">{esc(g["metric_label"])} · See the plan →</span></a>')
    return ('<section class="goal-index" id="golf-goals"><h2 class="gsect">What I’m working on</h2>'
            '<p class="goal-intro">Each goal has a baseline, a practice experiment and a record of what changes. '
            'The details live with that part of my game.</p>'
            '<div class="goal-index-grid">' + ''.join(cards) + '</div></section>')


def related(goals):
    active = [g for g in goals if g['status'] == 'active' and g['source'] == 'trackman']
    if not active:
        return ''
    return '<nav class="goal-related" aria-label="Practice goals"><b>Working on</b> ' + ' '.join(
        f'<a href="{goal_link(g)}">{esc(g["title"])} →</a>' for g in active) + '</nav>'


def chart(goal, rows):
    good = eligible(goal, rows)
    if not good:
        return '<p class="goal-note">The chart starts with the first qualifying session.</p>'
    vals = [r[goal['metric']] for r in good]
    lo, hi = min(vals + [goal['target']]) - 8, max(vals + [goal['target']]) + 8
    y = lambda v: 126 - (v - lo) / (hi - lo) * 100
    xs = [320] if len(good) == 1 else [48 + 544 * i / (len(good) - 1) for i in range(len(good))]
    points = ' '.join(f'{x:.1f},{y(v):.1f}' for x, v in zip(xs, vals))
    line = f'<polyline class="goal-series" points="{points}"/>' if len(good) > 1 else ''
    dots = ''.join(f'<circle class="goal-dot" cx="{x:.1f}" cy="{y(r[goal["metric"]]):.1f}" r="5">'
                   f'<title>{esc(r["date"])}: {fmt(r[goal["metric"]], goal["unit"])}; {r["n"]} shots</title></circle>'
                   for x, r in zip(xs, good))
    axis = (f'<text x="48" y="151">{esc(good[0]["date"])}</text>'
            f'<text x="592" y="151" text-anchor="end">{esc(good[-1]["date"])}</text>') if len(good) > 1 else (
                f'<text x="320" y="151" text-anchor="middle">{esc(good[0]["date"])}</text>')
    return (f'<svg class="goal-chart" viewBox="0 0 640 164" role="img" aria-label="{esc(goal["metric_label"])} by session; values in the table below">'
            f'<title>{esc(goal["title"])}: session medians and target</title>'
            f'<line class="goal-target" x1="48" x2="592" y1="{y(goal["target"]):.1f}" y2="{y(goal["target"]):.1f}"/>'
            f'<text x="592" y="{y(goal["target"]) - 8:.1f}" text-anchor="end">Goal {fmt(goal["target"], goal["unit"])}</text>'
            f'{line}{dots}{axis}</svg>')


def history(goal, rows):
    if not rows:
        return '<p class="goal-note">No measured sessions for this goal yet. Preview numbers are never used.</p>'
    trs = []
    for r in reversed(rows):
        small = ' · small sample' if r.get('n', 0) < goal.get('min_shots', 8) else ''
        trs.append(f'<tr><th scope="row">{esc(r["date"])}<small>{r.get("n", 0)} shots{small}</small></th>'
                   f'<td>{fmt(r[goal["metric"]], goal["unit"])}</td><td>{fmt(r.get("carry_best"), "yd")}</td>'
                   f'<td>{fmt(r.get("ball_speed"), "mph")}</td><td>{fmt(r.get("corridor_pct"), "%")}</td></tr>')
    return ('<div class="table-wrap"><table class="gtable goal-history"><caption>Recorded sessions, newest first</caption>'
            f'<thead><tr><th scope="col">Session</th><th scope="col">{esc(goal["metric_label"])}</th>'
            '<th scope="col">Best carry</th><th scope="col">Ball speed</th><th scope="col">Inside corridor</th></tr></thead>'
            '<tbody>' + ''.join(trs) + '</tbody></table></div>')


def training_section(goal):
    training = goal['analysis'].get('training')
    if not training:
        return ''
    exercises = ''.join(
        f'<li><b>{esc(e["name"])}</b> · {esc(e["dose"])}'
        f'<p>{esc(e["purpose"])} {esc(e["cue"])}</p></li>'
        for e in training['exercises'])
    sources = ' · '.join(f'<a href="{esc(s["url"])}">{esc(s["title"])}</a>'
                         for s in training['sources'])
    return (f'<section class="goal-training" aria-labelledby="{esc(goal["id"])}-training">'
            f'<h3 id="{esc(goal["id"])}-training">{esc(training["title"])}</h3>'
            f'<p>{esc(training["intro"])}</p><p class="goal-note">{esc(training["basis"])}</p>'
            '<div class="goal-columns"><div class="goal-experiment"><h4>A six-week trial</h4>'
            f'<p>{esc(training["schedule"])}</p><h4>Warm up first</h4><p>{esc(training["warmup"])}</p></div>'
            '<div><h4>Driver-speed practice</h4>'
            f'<p>{esc(training["speed"])}</p></div></div>'
            '<details class="goal-ranges" open><summary>Gym exercises · power first, then strength</summary>'
            f'<ol class="goal-priorities">{exercises}</ol></details>'
            '<h4>How to progress</h4>'
            f'<p>{esc(training["progression"])}</p><h4>Check that it transfers to carry</h4>'
            f'<p>{esc(training["review"])}</p><p class="goal-note">Training references: {sources}</p></section>')


def section(goal, tm):
    rows = observations(goal, tm)
    good = eligible(goal, rows)
    latest = good[-1] if good else {}
    current = latest.get(goal['metric'])
    gap = max(0, goal['target'] - current if goal['direction'] == 'higher' else current - goal['target']) if number(current) else None
    a = goal['analysis']
    metrics = [(goal['metric_label'], fmt(current, goal['unit'])),
               ('Best carry · same session', fmt(latest.get('carry_best'), 'yd')),
               ('Goal', fmt(goal['target'], goal['unit'])), ('Gap to goal', fmt(gap, goal['unit']))]
    metric_html = ''.join(f'<div><span class="lbl">{esc(label)}</span><strong>{value}</strong></div>' for label, value in metrics)
    latest_note = (f'Latest qualifying session: {esc(latest["date"])} · {latest["n"]} {esc(goal.get("club_label", goal["club"]))} shots. '
                   'Carry is measured before roll.') if latest else f'At least {goal.get("min_shots", 8)} measured shots are needed for a baseline.'
    if rows and rows[-1] is not latest and rows[-1].get('n', 0) < goal.get('min_shots', 8):
        latest_note += ' A newer small sample is listed below; the headline stays with the last qualifying session.'
    if len(good) == 1:
        trend_note = 'One qualifying session: a baseline, not a trend. New sessions will add points here.'
    elif len(good) > 1:
        change = good[-1][goal['metric']] - good[0][goal['metric']]
        trend_note = f'Change from the first qualifying session: {change:+.1f} {esc(goal["unit"])}. Each point is a session median, equally spaced; conditions may differ.'
    else:
        trend_note = 'Small samples remain visible in the table but do not establish progress.'
    if good and gap == 0:
        trend_note += ' Reaching the target in one session does not yet establish repeatability.'
    priorities = ''.join(f'<li><b>{esc(p["title"])}</b><p>{esc(p["text"])}</p></li>' for p in a['priorities'])
    ranges = ''.join(f'<tr><th scope="row">{esc(r["label"])}</th><td>{fmt(latest.get(r["key"]), r["unit"])}</td>'
                     f'<td>{esc(r["range"])}</td></tr>' for r in a['ranges'])
    explainers = ''.join(f'<details class="ex"><summary>{esc(e["title"])}</summary><div>{esc(e["text"])}</div></details>'
                        for e in a['explainers'])
    links = ' · '.join(f'<a href="{esc(s["url"])}">{esc(s["title"])}</a>' for s in a['sources'])
    return (f'<section class="golf-goal" id="{esc(goal["id"])}" aria-labelledby="{esc(goal["id"])}-title">'
            f'<div class="goal-heading"><div><span class="lbl">{esc(goal["category"])} · Goal</span>'
            f'<h2 id="{esc(goal["id"])}-title">{esc(goal["title"])}</h2><p>{esc(goal["description"])}</p></div>'
            f'<span class="goal-status">{esc(state(goal, rows))}</span></div>'
            f'<div class="goal-metrics">{metric_html}</div><p class="goal-note">{latest_note}</p>'
            '<div class="goal-columns"><div><h3>The initial read</h3>'
            f'<p>{esc(a["summary"])}</p><p class="goal-note">{esc(a["basis"])}</p>'
            f'<ol class="goal-priorities">{priorities}</ol></div>'
            f'<div class="goal-experiment"><span class="lbl">Next practice experiment</span><h3>{esc(a["experiment"]["title"])}</h3>'
            f'<p>{esc(a["experiment"]["text"])}</p><p>{esc(a["experiment"]["review"])}</p>'
            f'<p class="goal-note">{esc(goal["guardrail"])}</p></div></div>' + training_section(goal) +
            '<h3>Progress by session</h3>' + chart(goal, rows) + f'<p class="goal-note">{trend_note}</p>' + history(goal, rows) +
            '<details class="goal-ranges"><summary>Working ranges · provisional</summary>'
            '<p>Starting estimates to test, not requirements or guarantees. The current measurements update; these ranges stay dated until reviewed.</p>'
            '<div class="table-wrap"><table class="gtable goal-range-table"><thead><tr><th scope="col">Metric</th><th scope="col">Latest session</th><th scope="col">Working range</th></tr></thead>'
            f'<tbody>{ranges}</tbody></table></div></details><div class="ex-row">{explainers}</div>'
            f'<p class="goal-note">Analysis reviewed {esc(a["reviewed"])} · {links}</p>'
            '<a class="goal-back" href="golf.html#golf-goals">← All golf goals</a></section>')


def for_page(page, goals, tm):
    return ''.join(section(g, tm) for g in goals if g['page'] == page and g['status'] == 'active')
