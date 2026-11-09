#!/usr/bin/env python3
"""Privacy check for anything that reaches jackraney.com's PUBLIC repo or live site.

Two places run this same file:
- The owner's Mac, as a git pre-push hook on every copy of the site that can push, so a
  private line is stopped before it is public.
- The site's GitHub workflow (scripts/site_privacy.py, a byte-identical copy), before the
  daily robot commits its synced content and before anything is deployed to Pages.

Only lines ADDED by the commits in question are read, commit by commit, so words already
on the site never block an unrelated update, and a word added then removed is still caught
— including on a side branch that was merged. Everything else a push makes public is read
too: each commit message, the branch or tag name, and an annotated tag's message.
The word list is never in the public repo: listing private words there would publish them.
On the Mac it is a private config file; on GitHub it is the SITE_PRIVACY_RULES secret.

Fails closed: if the list is missing or unreadable, nothing goes out.
Messages name the kind of hit and the file, never the matched text.

    python3 site_privacy.py --pre-push <remote-name> <remote-url>   (git hook; refs on stdin)
    python3 site_privacy.py --scan-range <base> <head>              (cwd = repo; every commit)
    python3 site_privacy.py --scan-net <base> <head>                (the workflow: what a deploy shows)
    python3 site_privacy.py --scan-text <file>...                   (scan whole files)
    python3 site_privacy.py --sync-secret                           (Mac only: list -> GitHub secret)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ZERO = '0' * 40
HOOKS_DIR = Path(__file__).resolve().parent / 'site_git_hooks'
SITE_REPO = 'jraney99/jraney99.github.io'
SECRET = 'SITE_PRIVACY_RULES'


def _private(name: str) -> Path:
    """A registered file in the private agent repo. Only exists on the Mac."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from data_paths import path
    return path(name)


def rules_text() -> str:
    """The word list: the GitHub secret when the workflow sets it, else the private file."""
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        text = os.environ.get(SECRET, '')
        if not text.strip():
            raise ValueError(f'the {SECRET} secret is not set')
        return text
    return _private('site_privacy.json').read_text(encoding='utf-8')


def load_rules(rules_path: Path | None = None):
    """[(label, compiled regex)], [(label, compiled filename regex)]. Raises if unusable."""
    doc = json.loads(rules_path.read_text(encoding='utf-8') if rules_path else rules_text())
    text = [(r['label'], re.compile(r['pattern'], re.IGNORECASE)) for r in doc['text']]
    names = [(r['label'], re.compile(r['pattern'], re.IGNORECASE)) for r in doc['filenames']]
    if not text:
        raise ValueError('the word list is empty')
    return text, names


def scan_lines(lines_by_file: dict[str, list[str]], new_files: list[str], rules) -> list[tuple[str, str]]:
    """[(label, file)] for every rule that hits. One entry per (label, file)."""
    text_rules, name_rules = rules
    hits = []
    for f in new_files:
        for label, rx in name_rules:
            if rx.search(f) and (label, f) not in hits:
                hits.append((label, f))
    for f, lines in lines_by_file.items():
        for line in lines:
            for label, rx in text_rules:
                if rx.search(line) and (label, f) not in hits:
                    hits.append((label, f))
    return hits


def _collect_added(repo: Path, show: list[str], lines: dict[str, list[str]]) -> None:
    """Read one `git log -p` / `git diff` run and fold its ADDED lines into `lines`."""
    diff = subprocess.run(show, cwd=repo, capture_output=True, text=True, errors='replace', check=True).stdout
    current = None
    in_header = False   # between "diff --git" and the first "@@": "+++ b/x" is the file name, not content
    for row in diff.splitlines():
        if row.startswith('diff --git '):
            current, in_header = None, True
        elif in_header and row.startswith('+++ '):
            current = row[6:] if row.startswith('+++ b/') else None
            if current is not None:
                lines.setdefault(current, [])
        elif row.startswith('@@'):
            in_header = False
        elif not in_header and row.startswith('+') and current is not None:
            lines[current].append(row[1:])


def message_lines(repo: Path, rng: str) -> dict[str, list[str]]:
    """{'the message of commit abc1234': [its lines]} for every commit in the range.

    A commit message is as public as the files once it is pushed, and the likeliest one to
    name a private thing is the commit that takes it off a page ("drop the line about my doctor", naming them).
    Nothing read the messages until 2026-11-04 (test_a_private_word_in_a_commit_message...)."""
    out: dict[str, list[str]] = {}
    r = subprocess.run(['git', 'log', '--format=%x1e%h%x1f%B', rng], cwd=repo, capture_output=True,
                       text=True, errors='replace', check=True)
    for record in r.stdout.split('\x1e'):
        if '\x1f' not in record:
            continue
        short, body = record.split('\x1f', 1)
        out[f'the message of commit {short.strip()}'] = body.splitlines()
    return out


def added_lines(repo: Path, base: str, head: str, net: bool = False):
    """Lines added by EVERY commit in base..head, by file, plus the files any of them created.

    Commit by commit, not the net diff: a word added in one commit and removed in the next
    nets to nothing, but the first commit is still public history once pushed (caught by
    test_word_hidden_in_an_earlier_commit_of_the_same_push, 2026-11-03)."""
    if base == ZERO:
        # A brand-new ref: only the commits the remote's main does not already have.
        mb = subprocess.run(['git', 'merge-base', 'origin/main', head], cwd=repo, capture_output=True, text=True)
        rng = f'{mb.stdout.strip()}..{head}' if mb.returncode == 0 and mb.stdout.strip() else head
    else:
        rng = f'{base}..{head}'
    lines: dict[str, list[str]] = {}
    if net:
        # What a deploy would SHOW: the pages as they end up, not the history behind them.
        common = ['--no-color', '--no-ext-diff', '--no-renames', base, head]
        names = ['git', 'diff', '--name-status', *common]
        _collect_added(repo, ['git', 'diff', '-U0', *common], lines)
    else:
        base_args = ['--no-color', '--no-ext-diff', '--no-renames', '--format=', rng]
        names = ['git', 'log', '--name-status', '-m', '--first-parent', *base_args]
        # Two passes, because neither alone reads every line that would become public:
        # -m --first-parent is the only way to see what a merge itself contributes (a conflict
        # resolution lives in no parent), but it steps over the side branch's own commits, so a
        # word added and removed on a side branch slipped through the merge (2026-11-04,
        # test_word_hidden_on_a_merged_side_branch). --no-merges walks every one of those.
        _collect_added(repo, ['git', 'log', '-p', '-U0', '-m', '--first-parent', *base_args], lines)
        _collect_added(repo, ['git', 'log', '-p', '-U0', '--no-merges', *base_args], lines)
        # Messages only off the net path: --scan-net asks "what does the deployed site show",
        # and the commits behind it are already on GitHub by then, so holding the deploy back
        # for one of their messages would stop the site over something already public.
        lines.update(message_lines(repo, rng))
    status = subprocess.run(names, cwd=repo, capture_output=True, text=True, check=True).stdout
    new_files = sorted({r.split('\t', 1)[1] for r in status.splitlines() if r.startswith('A\t')})
    return lines, new_files


def describe(hits) -> str:
    shown = '; '.join(f'{label} in {f}' for label, f in hits[:4])
    more = f' (and {len(hits) - 4} more)' if len(hits) > 4 else ''
    return f'Privacy check held back this site update: {shown}{more}. Nothing was published.'


def check_range(repo: Path, base: str, head: str, rules, net: bool = False) -> list[tuple[str, str]]:
    lines, new_files = added_lines(repo, base, head, net)
    return scan_lines(lines, new_files, rules)


def ref_lines(repo: Path, local_ref: str, local_sha: str, remote_ref: str = '') -> dict[str, list[str]]:
    """The text a push carries besides file content: the branch or tag NAME it lands under, and
    an annotated tag's message. Both are public on GitHub the moment the push lands, and neither
    appears in any diff (2026-11-04, test_a_private_word_in_an_annotated_tag_message...).

    The remote ref is the name that becomes public: `git push origin HEAD:refs/heads/x` sends
    local_ref=HEAD, so reading only the local side missed it."""
    names = [n for n in (remote_ref, local_ref) if n and n != 'HEAD']
    out = {f'the name of {remote_ref or local_ref}': names}
    kind = subprocess.run(['git', 'cat-file', '-t', local_sha], cwd=repo, capture_output=True, text=True)
    if kind.stdout.strip() == 'tag':
        tag = subprocess.run(['git', 'cat-file', 'tag', local_sha], cwd=repo, capture_output=True,
                             text=True, errors='replace', check=True)
        # A tag object is headers, a blank line, then the message.
        body = tag.stdout.split('\n\n', 1)[1] if '\n\n' in tag.stdout else ''
        out[f'the message of tag {(remote_ref or local_ref).rsplit("/", 1)[-1]}'] = body.splitlines()
    return out


def pre_push(stdin_text: str, repo: Path) -> int:
    try:
        rules = load_rules()
    except Exception as e:  # noqa: BLE001 - fail closed: a public push with no check never goes out
        print(f'Privacy check could not run ({type(e).__name__}: its word list is unreadable), '
              f'so this site update was held back. Nothing was published.', file=sys.stderr)
        return 1
    hits = []
    for row in stdin_text.splitlines():
        parts = row.split()
        if len(parts) != 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if local_sha == ZERO:   # deleting a remote branch adds nothing
            continue
        refs = ref_lines(repo, local_ref, local_sha, remote_ref)
        hits += [h for h in scan_lines(refs, [], rules) if h not in hits]
        if remote_sha != ZERO:
            known = subprocess.run(['git', 'cat-file', '-e', f'{remote_sha}^{{commit}}'], cwd=repo,
                                   capture_output=True)
            if known.returncode != 0:   # remote moved past what we have: compare with what we know of it
                remote_sha = ZERO
        try:
            hits += [h for h in check_range(repo, remote_sha, local_sha, rules) if h not in hits]
        except subprocess.CalledProcessError as e:
            print(f'Privacy check could not read the outgoing changes (git exited {e.returncode}), '
                  f'so this site update was held back. Nothing was published.', file=sys.stderr)
            return 1
    if hits:
        print(describe(hits), file=sys.stderr)
        return 1
    return 0


def install(repo: Path) -> None:
    """Point a site copy at the shared hook. Idempotent; called by every publisher on sync."""
    subprocess.run(['git', 'config', 'core.hooksPath', str(HOOKS_DIR)], cwd=repo, check=True,
                   capture_output=True)


def site_clones(home: Path | None = None, skills: Path | None = None) -> list[Path]:
    """Every copy of the site on this Mac that can push, Jack's own working clone first.

    That clone (~/jackraney-site) is the one he and Claude sessions edit by hand, and it is
    where an unreviewed push is most likely to come from — but until 2026-11-04 only the three
    publisher skills installed the hook, on their own clones, so the hand-edited one was the
    single copy with no check at all."""
    home = home or Path.home()
    skills = skills or Path(__file__).resolve().parents[1]
    found = [home / 'jackraney-site', *sorted(skills.glob('*/state/site-repo'))]
    return [p for p in found if (p / '.git').exists()]


def install_all(required: Path, home: Path | None = None, skills: Path | None = None) -> list[Path]:
    """Install the hook on `required` (raising if that fails) and on every other site copy.

    A publisher must not start a run whose own clone is unhooked, but it also must not abort
    because some other copy could not be configured — it says so and carries on."""
    install(required)
    done = [required]
    for repo in site_clones(home, skills):
        if repo.resolve() == required.resolve():
            continue
        try:
            install(repo)
            done.append(repo)
        except subprocess.CalledProcessError as e:
            print(f'the privacy hook could not be set on the site copy at {repo} '
                  f'(git config exited {e.returncode}); pushes from THAT copy are unchecked',
                  file=sys.stderr)
    return done


def rules_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def sync_secret() -> int:
    """Copy the private word list into the site repo's GitHub secret, and remember which
    version went up so test_site_privacy can tell when the two have drifted apart."""
    text = _private('site_privacy.json').read_text(encoding='utf-8')
    load_rules(None)   # never upload a list that would not load
    r = subprocess.run(['/opt/homebrew/bin/gh', 'secret', 'set', SECRET, '-R', SITE_REPO], input=text,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f'gh secret set failed: {r.stderr.strip()[:300]}', file=sys.stderr)
        return 1
    _private('site_privacy_secret_sync.json').write_text(json.dumps({'sha256': rules_hash(text)}) + '\n')
    print('secret updated')
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ['--pre-push']:
        return pre_push(sys.stdin.read(), Path.cwd())
    if argv[:1] == ['--sync-secret']:
        return sync_secret()
    if argv[:1] in (['--scan-range'], ['--scan-net']) and len(argv) == 3:
        try:
            rules = load_rules()
        except Exception as e:  # noqa: BLE001 - fail closed: nothing is published unchecked
            print(f'Privacy check could not run ({type(e).__name__}: {e}), so nothing was published.',
                  file=sys.stderr)
            return 1
        try:
            hits = check_range(Path.cwd(), argv[1], argv[2], rules, net=argv[0] == '--scan-net')
        except subprocess.CalledProcessError as e:
            print(f'Privacy check could not read the changes (git exited {e.returncode}), '
                  f'so nothing was published.', file=sys.stderr)
            return 1
        print(describe(hits) if hits else 'Privacy check: clean')
        return 1 if hits else 0
    if argv[:1] == ['--scan-text'] and len(argv) >= 2:
        rules = load_rules()
        lines = {f: Path(f).read_text(encoding='utf-8', errors='replace').splitlines() for f in argv[1:]}
        hits = scan_lines(lines, [], rules)
        print(describe(hits) if hits else 'clean')
        return 1 if hits else 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
