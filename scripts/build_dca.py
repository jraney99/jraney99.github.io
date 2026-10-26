"""Recalculate the $10-a-day bitcoin page (bitcoin-dca.html) from daily prices.

Run from the repo root: python3 scripts/build_dca.py [--offline]

- Prices are cached in data/btc_daily.json (Coinbase BTC-USD daily closes, UTC) and data/spy_daily.json
  (SPY dividend-adjusted closes, Yahoo Finance). Only missing days are fetched. If a fetch fails, the
  cache is used as is, so the page is never broken by an outage, only a day behind.
- Numbers that move go into data/facts.json under dca.* keys (filled into <span data-fact> by
  build_facts.py). The chart and the year table are redrawn between their markers. Meta descriptions,
  the home card and the Writing list blurb are updated in place.
- Historical sentences (the 2018 and 2022 drawdowns) are not touched; they describe the past.
"""
import json
import math
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_status import record  # noqa: E402
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'bitcoin-dca.html')
BTC = os.path.join(ROOT, 'data', 'btc_daily.json')
SPY = os.path.join(ROOT, 'data', 'spy_daily.json')
FACTS = os.path.join(ROOT, 'data', 'facts.json')
START = date(2017, 1, 1)
DAILY = 10
UA = {'User-Agent': 'Mozilla/5.0 (jackraney.com DCA page)'}


def load(path):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}


def save(path, data):
    text = json.dumps(data, indent=0, sort_keys=True) + '\n'
    if not os.path.exists(path) or open(path, encoding='utf-8').read() != text:
        open(path, 'w', encoding='utf-8').write(text)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.loads(r.read())


def fetch_btc(cache):
    last_full = datetime.now(timezone.utc).date() - timedelta(days=1)  # today's candle is not closed yet
    day = max((date.fromisoformat(d) for d in cache), default=START - timedelta(days=1)) + timedelta(days=1)
    while day <= last_full:
        end = min(day + timedelta(days=299), last_full)
        rows = get('https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400'
                   f'&start={day.isoformat()}T00:00:00Z&end={end.isoformat()}T00:00:00Z')
        for t, low, high, open_, close, vol in rows:
            d = datetime.fromtimestamp(t, timezone.utc).date()
            if START <= d <= last_full:
                cache[d.isoformat()] = close
        day = end + timedelta(days=1)
        time.sleep(0.4)
    return cache


def fetch_spy():
    end = int(time.time())
    d = get(f'https://query1.finance.yahoo.com/v8/finance/chart/SPY?period1=1483228800&period2={end}&interval=1d')
    r = d['chart']['result'][0]
    adj = r['indicators']['adjclose'][0]['adjclose']
    return {datetime.fromtimestamp(t, timezone.utc).date().isoformat(): a for t, a in zip(r['timestamp'], adj) if a}


def simulate(btc, through):
    """Buy $10 at every daily close from START through `through`. Returns per-day (date, put_in, coins, price)."""
    out, coins, put = [], 0.0, 0
    d = START
    while d <= through:
        price = btc.get(d.isoformat())
        if price is None:
            raise SystemExit(f'missing BTC close for {d}')
        coins += DAILY / price
        put += DAILY
        out.append((d, put, coins, price))
        d += timedelta(days=1)
    return out


def spy_value(spy, through):
    """$10 a day into SPY, weekend and holiday purchases at the prior close; valued at the last close."""
    if not spy:
        return None
    days = sorted(spy)
    last = None
    shares = 0.0
    d, i = START, 0
    first_price = spy[days[0]]
    while d <= through:
        while i < len(days) and days[i] <= d.isoformat():
            last = spy[days[i]]
            i += 1
        shares += DAILY / (last or first_price)
        d += timedelta(days=1)
    return shares * (last or first_price)


def money(x, k=False):
    if k:
        return f'${x / 1000:,.0f}K'
    return f'${x:,.0f}'


def long_date(d):
    return f'{d.strftime("%B")} {d.day}, {d.year}'


def chart(rows):
    daily = rows
    """Weekly points; same look as the original Exhibit 1."""
    x0, x1, y0, y1 = 62, 704, 20, 320
    pts = rows[::7] + ([rows[-1]] if (len(rows) - 1) % 7 else [])
    top_val = max(v for _, _, v in daily)
    step = 100000
    top = math.ceil(top_val / step) * step
    first, last = pts[0][0], pts[-1][0]
    span = (last - first).days or 1
    X = lambda d: x0 + (d - first).days / span * (x1 - x0)
    Y = lambda v: y1 - v / top * (y1 - y0)
    out = []
    for g in range(0, top + 1, step):
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                   f'<text x="{x0 - 8}" y="{Y(g) + 4:.1f}" class="yl">${g // 1000}K</text>')
    for yr in range(first.year, last.year + 1):
        d = date(yr, 1, 1)
        if first <= d <= last:
            out.append(f'<text x="{X(d):.1f}" y="344" class="xl">{yr}</text>')
    area = ' '.join(f'L{X(d):.1f},{Y(v):.1f}' for d, _, v in pts)
    out.append(f'<path d="M{X(first):.1f},{Y(0):.1f} {area} L{X(last):.1f},{Y(0):.1f} Z" class="area"/>')
    out.append('<polyline points="' + ' '.join(f'{X(d):.1f},{Y(v):.1f}' for d, _, v in pts) + '" class="val"/>')
    out.append('<polyline points="' + ' '.join(f'{X(d):.1f},{Y(p):.1f}' for d, p, _ in pts) + '" class="inv"/>')

    def mark(d, v, label, below=False):
        anchor = 'end' if X(d) > x1 - 60 else 'middle'
        out.append(f'<circle cx="{X(d):.1f}" cy="{Y(v):.1f}" r="4" class="dot"/>'
                   f'<text x="{X(d):.1f}" y="{Y(v) + (18 if below else -10):.1f}" class="ml" text-anchor="{anchor}">{label}</text>')

    def peak(a, b):
        sel = [(d, v) for d, _, v in daily if a <= d <= b]
        return max(sel, key=lambda t: t[1]) if sel else None

    def trough(a, b):
        sel = [(d, v) for d, _, v in daily if a <= d <= b]
        return min(sel, key=lambda t: t[1]) if sel else None
    for d, v in filter(None, [peak(date(2017, 10, 1), date(2018, 1, 31)), peak(date(2021, 9, 1), date(2021, 12, 31))]):
        mark(d, v, f'{d.strftime("%b %Y")}: {money(v, True)}')
    t = trough(date(2022, 6, 1), date(2022, 12, 31))
    if t:
        mark(t[0], t[1], f'{t[0].strftime("%b %Y")}: {money(t[1], True)}', below=True)
    ath = max(daily, key=lambda p: p[2])
    if ath[0] != last:
        mark(ath[0], ath[2], f'{ath[0].strftime("%b %Y")}: {money(ath[2], True)}')
    mark(last, pts[-1][2], f'Today: {money(pts[-1][2], True)}', below=ath[0] != last)
    return '\n'.join(out)


def table(rows):
    by_day = {d: (p, c * price) for d, p, c, price in rows}
    out = []
    for yr in range(START.year, rows[-1][0].year):
        p, v = by_day[date(yr, 12, 31)]
        out.append(f'<tr><th scope="row">End of {yr}</th><td>{money(p)}</td><td>{money(v)}</td><td>{v / p:.1f}x</td></tr>')
    d, p, c, price = rows[-1]
    v = c * price
    out.append(f'<tr class="total"><th scope="row">{d.strftime("%b")} {d.day}, {d.year}</th><td>{money(p)}</td>'
               f'<td>{money(v)}</td><td>{v / p:.1f}x</td></tr>')
    return '\n'.join(out)


def replace_region(page, name, body):
    a, b = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
    i, j = page.index(a) + len(a), page.index(b)
    return page[:i] + '\n' + body + '\n' + page[j:]


def main():
    offline = '--offline' in sys.argv
    btc, spy = load(BTC), load(SPY)
    if not offline:
        try:
            btc = fetch_btc(btc)
            save(BTC, btc)
            record('bitcoin_prices', True)
        except Exception as e:  # noqa: BLE001 - keep the cached prices
            print(f'BTC fetch failed, using cache: {e}')
            record('bitcoin_prices', False, 'Coinbase prices could not be fetched; the page shows the last day it had.')
        try:
            fresh = fetch_spy()
            if len(fresh) > 1000:
                spy = fresh
                save(SPY, spy)
        except Exception as e:  # noqa: BLE001
            print(f'SPY fetch failed, using cache: {e}')
    if not btc:
        raise SystemExit('no BTC prices')
    through = max(date.fromisoformat(d) for d in btc)
    rows = simulate(btc, through)
    d, put, coins, price = rows[-1]
    value = coins * price
    daily = [(r[0], r[1], r[2] * r[3]) for r in rows]
    ath_d, _, ath_v = max(daily, key=lambda r: r[2])
    below = 1 - value / ath_v
    lump = put / btc[START.isoformat()] * price
    under = sum(1 for _, p, v in daily if v < p)
    spy_v = spy_value(spy, through)

    if ath_d == d:
        today_line = f'As of {long_date(d)}, the account is at a new all-time high.'
    else:
        today_line = (f'The all-time high was {money(round(ath_v, -3))} on {long_date(ath_d)}. '
                      f'As of {long_date(d)}, the account is {below:.0%} below it.')
    lump_txt = f'about ${lump / 1e6:.1f} million' if lump >= 1e6 else f'about {money(round(lump, -3))}'
    facts = {
        'dca.through': long_date(d),
        'dca.through_short': f'{d.strftime("%B")} {d.day}',
        'dca.days': f'{len(rows):,}',
        'dca.put_in': money(put),
        'dca.btc': f'{coins:.2f}',
        'dca.value': money(round(value, -3)),
        'dca.value_k': money(value, True),
        'dca.close': money(price),
        'dca.multiple': f'{value / put:.1f}',
        'dca.avg_cost': money(round(put / coins, -1)),
        'dca.today_line': today_line,
        'dca.days_under': str(under),
        'dca.lump': lump_txt,
        'dca.first_close': money(btc[START.isoformat()]),
    }
    if spy_v:
        facts['dca.spy_value'] = money(round(spy_v, -2))
        facts['dca.spy_multiple'] = f'{spy_v / put:.1f}'
    all_facts = load(FACTS)
    if any(all_facts.get(k) != v for k, v in facts.items()):
        all_facts.update(facts)
        open(FACTS, 'w', encoding='utf-8').write(json.dumps(all_facts, indent=1, ensure_ascii=False) + '\n')

    page = open(PAGE, encoding='utf-8').read()
    new = replace_region(page, 'dca-chart', chart(daily))
    new = replace_region(new, 'dca-table', table(rows))
    blurb = f'{money(put)} in, about {money(round(value, -3))} out, and two drops of more than 75% along the way.'
    new = re.sub(r'(<meta property="og:description" content=")[^"]*', lambda m: m.group(1) + blurb, new)
    if new != page:
        open(PAGE, 'w', encoding='utf-8').write(new)
        print('bitcoin-dca.html updated')
    for path, pat in ((os.path.join(ROOT, 'index.html'), r'(<a class="memo-card memo-card--stack" href="bitcoin-dca.html">[\s\S]*?<p class="memo-card__dek">)[^<]*'),
                      (os.path.join(ROOT, 'data', 'writing.json'), r'("url": "bitcoin-dca.html"[^\n]*"dek": ")[^"]*')):
        s = open(path, encoding='utf-8').read()
        t = re.sub(pat, lambda m: m.group(1) + blurb, s, count=1)
        if t != s:
            open(path, 'w', encoding='utf-8').write(t)
    print(f'DCA through {d}: {money(value)} ({value / put:.1f}x)')


if __name__ == '__main__':
    main()
