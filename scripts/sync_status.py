"""Record whether each automatic data source worked, in data/sync_status.json (public, no secrets).

Archibald's site-health check reads the live copy and messages Jack only when a source is failing.
A source's entry changes only when its state flips, so a quiet day makes no commit.
"""
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'data', 'sync_status.json')


def record(source, ok, note=''):
    data = json.load(open(PATH)) if os.path.exists(PATH) else {}
    prev = data.get(source, {})
    if prev.get('ok') == ok and prev.get('note') == note:
        return
    data[source] = {'ok': ok, 'note': note, 'since': date.today().isoformat()}
    open(PATH, 'w').write(json.dumps(data, indent=1, sort_keys=True) + '\n')
