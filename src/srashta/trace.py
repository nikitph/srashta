#!/usr/bin/env python3
"""Walk the chain in either direction.

  up   : why does this exist?        commit -> ticket -> requirement -> decision
  down : what breaks if I change it? requirement -> tickets -> tests -> commits

Every edge already exists in the data. This only refuses to lose them.
"""
import json, os, re, subprocess, sys
from collections import defaultdict
from .common import out, read_json

def git_commits_for(ticket, root='.'):
    try:
        r = subprocess.run(['git', 'log', '--oneline', '--all', f'--grep={ticket}'],
                           cwd=root, capture_output=True, text=True, timeout=10)
        return [l for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        return []

def load(cfg):
    reqs = {r['id']: r for r in read_json(out(cfg, 'requirements.assigned.json'))}
    tickets = []
    d = out(cfg, 'tickets')
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith('.json'): tickets += read_json(os.path.join(d, f))
    return reqs, tickets

def main(cfg, target):
    reqs, tickets = load(cfg)
    owns = defaultdict(list); asserts = defaultdict(list)
    for t in tickets:
        for r in t['requirements']: owns[r].append(t)
        for r in t.get('asserts', []): asserts[r].append(t)

    if target in reqs:                                    # downward
        r = reqs[target]
        print(f"\n  {target}  [{r['priority']}]  {r['module']} · phase {r['phase']}")
        print(f"  {r['text'][:300]}\n")
        print(f"  phase assigned because: {r.get('phase_reason')}")
        o = owns.get(target, []); a = asserts.get(target, [])
        print(f"\n  WHAT DEPENDS ON THIS")
        for t in o:
            kind = 'supports' if t['kind'] == 'contract' else 'OWNS'
            print(f"    {t['id']:6s} {kind:9s} {t['title']}")
            for i, at in enumerate(t['acceptance_tests'], 1):
                print(f"           test {i}: {at}")
            for c in git_commits_for(t['id']): print(f"           commit  {c}")
        for t in a:
            print(f"    {t['id']:6s} asserts   {t['title']}")
        if not o and not a:
            print("    nothing - this requirement is not yet decomposed")
        print()
        return 0

    tk = next((t for t in tickets if t['id'] == target), None)
    if tk:                                                # upward
        print(f"\n  {tk['id']}  {tk['title']}   ({tk['kind']}, wave {tk['wave']})")
        print(f"\n  EXISTS BECAUSE OF")
        for rid in tk['requirements']:
            r = reqs.get(rid)
            if r: print(f"    {rid}  [{r['priority']}]  {r['text'][:200]}")
        if tk['depends_on']:
            print(f"\n  BUILDS ON   {', '.join(tk['depends_on'])}")
        if tk['contracts_used']:
            print(f"  CONSTRAINED BY   {', '.join(tk['contracts_used'])}")
        cs = git_commits_for(tk['id'])
        if cs:
            print(f"\n  COMMITS")
            for c in cs: print(f"    {c}")
        print()
        return 0

    m = re.search(r'\b([CTI]-\d{2,3}[a-z]?)\b', target)   # a commit message or sha
    if m: return main(cfg, m.group(1))
    print(f"  '{target}' is not a requirement id, a ticket id, or a string containing one")
    return 1
