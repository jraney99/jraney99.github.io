"""Apply public-display preferences before golf data is rendered or published.

Private source records stay intact. Fingerprints avoid spelling excluded names
out in this public repository; they are matching keys, not encryption.
"""
import hashlib
import json
import re
from pathlib import Path


def fingerprint(name):
    normalized = re.sub(r'[^a-z0-9]', '', str(name).casefold())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def redact_round_names(value, excluded):
    if isinstance(value, list):
        return [redact_round_names(item, excluded) for item in value]
    if isinstance(value, dict):
        return {key: ('Private course' if key == 'course' and fingerprint(item) in excluded
                      else redact_round_names(item, excluded)) for key, item in value.items()}
    return value


def apply(root):
    root = Path(root)
    policy = json.loads((root / 'data/golf-privacy.json').read_text(encoding='utf-8'))
    excluded = set(policy['excluded_course_fingerprints'])
    changed = []
    for filename in ('courses.json', 'golf.json', 'golf-stats.json'):
        path = root / 'data' / filename
        if not path.exists():
            continue
        original = json.loads(path.read_text(encoding='utf-8'))
        public = redact_round_names(original, excluded)
        if filename == 'courses.json':
            public['courses'] = [course for course in public.get('courses', [])
                                 if fingerprint(course.get('name', '')) not in excluded]
        if public != original:
            path.write_text(json.dumps(public, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
            changed.append(filename)
    return changed
