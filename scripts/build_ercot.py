"""Yearly ERCOT refresh: the calculator, the miners memo numbers and the home share image move to the
latest complete year of ERCOT real-time hub prices.

Run from the repo root: python3 scripts/build_ercot.py [--year 2026] [--check]

ERCOT publishes report NP6-785-ER (RTMLZHBSPP_<year>) on January 1 for the year just ended. This
script finds the newest complete year, downloads it, averages the 15-minute settlement point prices to
hours (hour ending, Central Prevailing Time; the repeated fall-back hour is its own hour, so a
year has 8,760 or 8,784 hours, matching the original 2025 file), and writes assets/data/ercot.js. It then recomputes every number
the site quotes from that data into data/facts.json under ercot.* keys.

If ERCOT is unreachable or the newest file is not a complete year, nothing changes.
--check recomputes the current year's file and compares it with assets/data/ercot.js (no writes).
"""
import io
import json
import os
import statistics
import sys
import urllib.request
import zipfile
from collections import OrderedDict
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'data', 'ercot.js')
FACTS = os.path.join(ROOT, 'data', 'facts.json')
HUBS = ['HB_WEST', 'HB_NORTH', 'HB_HOUSTON', 'HB_SOUTH']
LIST = 'https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13061'
DOWNLOAD = 'https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}'
UA = {'User-Agent': 'Mozilla/5.0 (jackraney.com yearly ERCOT refresh)'}
SHUTOFF = 100  # $/MWh, the memo's example shut-off price


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        data = r.read()
    return data if binary else json.loads(data)


def newest_complete_year():
    docs = [d['Document'] for d in get(LIST)['ListDocsByRptTypeRes']['DocumentList']]
    best = None
    for d in docs:
        name = d['FriendlyName']
        if not name.startswith('RTMLZHBSPP_'):
            continue
        year = int(name.split('_')[1])
        published = date.fromisoformat(d['PublishDate'][:10])
        if published.year > year and (best is None or year > best[0]):  # complete only after the year ends
            best = (year, d['DocID'], d['PublishDate'][:10])
    return best


def hourly(xlsx_bytes, year):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    sums = {h: OrderedDict() for h in HUBS}
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        head = [str(c).strip() if c is not None else '' for c in next(rows)]
        ix = {k: head.index(k) for k in ('Delivery Date', 'Delivery Hour', 'Repeated Hour Flag', 'Settlement Point Name', 'Settlement Point Price')}
        for r in rows:
            hub = r[ix['Settlement Point Name']]
            if hub not in sums:
                continue
            d = r[ix['Delivery Date']]
            d = d.date() if isinstance(d, datetime) else datetime.strptime(str(d), '%m/%d/%Y').date()
            key = (d.isoformat(), int(r[ix['Delivery Hour']]), str(r[ix['Repeated Hour Flag']]).strip().upper() == 'Y')
            s = sums[hub].setdefault(key, [Decimal(0), 0])
            s[0] += Decimal(str(r[ix['Settlement Point Price']]))
            s[1] += 1
    out = {}
    for hub, s in sums.items():
        keys = sorted(s)
        out[hub] = [float((s[k][0] / s[k][1]).quantize(Decimal('0.01'), ROUND_HALF_UP)) for k in keys]
        if not 8700 <= len(out[hub]) <= 8800 or any(k[0][:4] != str(year) for k in keys):
            raise SystemExit(f'{hub}: unexpected shape ({len(out[hub])} hours)')
    return out, sorted(sums['HB_WEST'])


def stats(prices, keys):
    """Every ERCOT number the site quotes, from West hub hourly prices."""
    n = len(prices)
    total = sum(prices)
    median = statistics.median(prices)
    top = max(range(n), key=lambda i: prices[i])
    d, he, _ = keys[top]
    day = date.fromisoformat(d)
    k = max(1, round(n * 0.01))
    top_share = sum(sorted(prices, reverse=True)[:k]) / total
    above = [p for p in prices if p > SHUTOFF]
    kept = total - sum(above)
    cut = 1 - kept / total
    run = 1 - len(above) / n
    saved_per_mw = sum(above)  # $ per MW-year avoided by sitting out those hours

    def hour_label(h):
        def fmt(x):
            x = x % 24
            return f'{12 if x % 12 == 0 else x % 12} {"a.m." if x < 12 else "p.m."}'
        a, b = fmt(h - 1), fmt(h)
        same = a.split()[1] == b.split()[1]
        return f'{a.split()[0]} to {b}' if same else f'{a} to {b}'
    return {
        'ercot.year': str(day.year),
        'ercot.hours_in_year': f'{n:,}',
        'ercot.median': f'${median:,.2f}',
        'ercot.max': f'${prices[top]:,.2f}',
        'ercot.max_short': f'${prices[top]:,.0f}',
        'ercot.max_when': f'{hour_label(he)} on {day.strftime("%B")}&nbsp;{day.day}',
        'ercot.max_multiple': f'{round(prices[top] / median, -1):.0f}' if prices[top] / median >= 20 else f'{prices[top] / median:.0f}',
        'ercot.top1_hours': str(k),
        'ercot.top1_share': f'{top_share:.1%}',
        'ercot.hours_above': f'{len(above):,}',
        'ercot.bill_cut': f'{cut:.0%}',
        'ercot.run_share': f'{run:.1%}',
        'ercot.saved_per_mw': f'${round(saved_per_mw, -3):,.0f}',
    }


def write_js(year, hubs, published):
    head = (f'// ERCOT real-time hub prices, {year}. Hourly averages of 15-minute settlement point prices, in $/MWh.\n'
            f'// Source: ERCOT, Historical RTM Load Zone and Hub Prices (NP6-785-ER), file RTMLZHBSPP_{year}, published {published}.\n'
            f'// Hours run in order from hour ending 1:00 on January 1 through hour ending 24:00 on December 31, Central Prevailing Time.\n')
    body = json.dumps({'year': year, 'units': '$/MWh', 'hubs': hubs}, separators=(',', ':'))
    text = head + f'window.ERCOT = {body};\nwindow.ERCOT_2025 = window.ERCOT; // older scripts\n'
    if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
        open(OUT, 'w', encoding='utf-8').write(text)
        return True
    return False


def current_year():
    if not os.path.exists(OUT):
        return None
    s = open(OUT, encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.index(';\n', s.index('{'))])['year']


def main():
    check = '--check' in sys.argv
    want = int(sys.argv[sys.argv.index('--year') + 1]) if '--year' in sys.argv else None
    try:
        found = newest_complete_year()
    except Exception as e:  # noqa: BLE001 - ERCOT down: keep what we have
        print(f'ERCOT list unavailable: {e}')
        return
    if not found:
        print('no complete year found')
        return
    year, doc, published = found
    if want:
        docs = [d['Document'] for d in get(LIST)['ListDocsByRptTypeRes']['DocumentList']]
        match = [d for d in docs if d['FriendlyName'] == f'RTMLZHBSPP_{want}']
        if not match:
            raise SystemExit(f'no file for {want}')
        year, doc, published = want, match[0]['DocID'], match[0]['PublishDate'][:10]
    have = current_year()
    if not check and not want and have == year:
        print(f'ERCOT data already {year}')
        return
    z = zipfile.ZipFile(io.BytesIO(get(DOWNLOAD.format(doc), binary=True)))
    xlsx = z.read([n for n in z.namelist() if n.endswith('.xlsx')][0])
    hubs, keys = hourly(xlsx, year)
    pub = datetime.strptime(published, '%Y-%m-%d')
    pub_txt = f'{pub.strftime("%B")} {pub.day}, {pub.year}'
    if check:
        s = open(OUT, encoding='utf-8').read()
        old = json.loads(s[s.index('{'):s.index(';\n', s.index('{'))])['hubs']
        diffs = {h: sum(1 for a, b in zip(old[h], hubs[h]) if abs(a - b) > 0.006) for h in HUBS}
        print('hours that differ by hub:', diffs, '| stats:', json.dumps(stats(hubs['HB_WEST'], keys), indent=1))
        return
    write_js(year, hubs, pub_txt)
    facts = json.load(open(FACTS, encoding='utf-8'))
    facts.update(stats(hubs['HB_WEST'], keys))
    facts['ercot.published'] = pub_txt
    open(FACTS, 'w', encoding='utf-8').write(json.dumps(facts, indent=1, ensure_ascii=False) + '\n')
    print(f'ERCOT data now {year}')


if __name__ == '__main__':
    main()
