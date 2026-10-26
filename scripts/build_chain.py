"""Keep the bitcoin halving lines current from the live block height.

Run from the repo root: python3 scripts/build_chain.py [--offline]

The block reward halves every 210,000 blocks. This reads the current height from mempool.space, works
out the reward era, and updates btc.* facts ("now 3.125 BTC", "Since the April 2024 halving") and the
issuance table on bitcoin-rules.html. A halving date is recorded in data/chain.json the first day a new
era is seen. If the height can't be fetched, nothing changes.
"""
import json
import os
import sys
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, 'data', 'chain.json')
FACTS = os.path.join(ROOT, 'data', 'facts.json')
PAGE = os.path.join(ROOT, 'bitcoin-rules.html')
KNOWN = {1: '2012-11-28', 2: '2016-07-09', 3: '2020-05-11', 4: '2024-04-20'}  # actual halving dates


def reward(era):
    r = 50 / 2 ** era
    return f'{r:.8f}'.rstrip('0').rstrip('.')


def coins(era):
    n = 210000 * 50 / 2 ** era
    if n >= 1e6:
        return f'{n / 1e6:g}M'
    return f'{n:,.0f}' if n == int(n) else f'{n:,.3f}'.rstrip('0').rstrip('.')


def table(era, halvings):
    years = {0: 2009}
    years.update({e: int(d[:4]) for e, d in halvings.items()})
    rows = []
    for e in range(0, era + 1):
        start = years[e] if e in years else years[e - 1] + 4
        end = f'{years[e + 1]}' if e + 1 in years else f'~{start + 4}'
        rows.append(f'<tr><th scope="row">{start} to {end}</th><td>{reward(e)}</td><td>{coins(e)}</td></tr>')
    rows.append('<tr><th scope="row">Every period after</th><td>Half the last</td><td>Half the last</td></tr>')
    return '\n'.join('              ' + r for r in rows)


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if '--offline' not in sys.argv:
        try:
            req = urllib.request.Request('https://mempool.space/api/blocks/tip/height', headers={'User-Agent': 'jackraney.com'})
            state['height'] = int(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:  # noqa: BLE001
            print(f'block height unavailable, keeping last: {e}')
    height = state.get('height')
    if not height:
        print('no block height yet')
        return
    era = height // 210000
    halvings = {int(k): v for k, v in state.get('halvings', {}).items()}
    halvings.update({k: v for k, v in KNOWN.items()})
    if era not in halvings and era > 0:
        halvings[era] = date.today().isoformat()  # first day we saw the new era
    state['halvings'] = {str(k): v for k, v in sorted(halvings.items())}
    open(STATE, 'w').write(json.dumps(state, indent=1) + '\n')

    last = date.fromisoformat(halvings[era])
    facts = json.load(open(FACTS, encoding='utf-8'))
    new = {'btc.subsidy': reward(era), 'btc.last_halving': f'{last.strftime("%B")} {last.year}'}
    if any(facts.get(k) != v for k, v in new.items()):
        facts.update(new)
        open(FACTS, 'w', encoding='utf-8').write(json.dumps(facts, indent=1, ensure_ascii=False) + '\n')
    page = open(PAGE, encoding='utf-8').read()
    a, b = '<!-- halvings:start -->', '<!-- halvings:end -->'
    i, j = page.index(a) + len(a), page.index(b)
    out = page[:i] + '\n' + table(era, {k: v for k, v in halvings.items() if k <= era}) + '\n              ' + page[j:]
    if out != page:
        open(PAGE, 'w', encoding='utf-8').write(out)
        print('issuance table updated')
    print(f'height {height}, era {era}, reward {reward(era)}')


if __name__ == '__main__':
    main()
