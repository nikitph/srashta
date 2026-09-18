#!/usr/bin/env python3
"""Which tickets may be claimed right now.

This is a PURE FUNCTION of the ticket graph plus merge state. No model, no judgment.
That is the point: an orchestrator does not need to understand the product to schedule
it correctly, so any scheduler - Multica, Symphony, a cron job, a person - gets the
same answer.

  python3 pipeline/eligible.py 0                      # nothing merged yet
  python3 pipeline/eligible.py 0 --state state.json   # {"C-01":"merged","C-02":"in_progress"}
"""
import argparse, json, os, sys
from collections import defaultdict
from .common import load_project, out, read_json

DONE = {'merged'}
BUSY = {'in_progress', 'claimed', 'review', 'in_review'}

def eligible(tickets, state):
    by_id = {t['id']: t for t in tickets}
    unknown = set(state) - set(by_id)
    invalid = set(state.values()) - (DONE | BUSY | {'todo', 'blocked', 'failed'})
    if unknown or invalid: raise ValueError(f'invalid execution state: tickets={sorted(unknown)}, statuses={sorted(invalid)}')
    done = {k for k, v in state.items() if v in DONE}
    busy = {k for k, v in state.items() if v in BUSY}
    claimable, held = [], []
    for t in tickets:
        if t['id'] in done: continue
        if t['id'] in busy:
            held.append((t['id'], state[t['id']])); continue
        if t['blocked_on']:
            held.append((t['id'], f"blocked on {', '.join(t['blocked_on'])}")); continue
        missing = [d for d in t['depends_on'] if d not in done]
        if missing:
            held.append((t['id'], f"waiting on {', '.join(missing)}")); continue
        claimable.append(t)
    # Disjoint file ownership is checked WITHIN a wave. Releasing the next wave while
    # this one is still in flight therefore hands out tickets whose disjointness nobody
    # verified - and prints "all concurrent" while it is untrue. A wave is not released
    # until every ticket in the one before it is done.
    lowest = min((t['wave'] for t in claimable), default=None)
    if lowest is None:
        return [], [], held
    unfinished = sorted({t['wave'] for t in tickets
                         if t['wave'] < lowest and t['id'] not in done})
    if unfinished:
        for t in claimable:
            held.append((t['id'], f"wave {t['wave']} waits for wave "
                                  f"{unfinished[0]} to finish"))
        return [], [], held
    now = [t for t in claimable if t['wave'] == lowest]
    return now, [t for t in claimable if t['wave'] != lowest], held

def run(cfg, phase, state_path=None, as_json=False):
    from .validate import check
    *_, errors, _ = check(cfg, phase)
    if errors: raise ValueError('\n'.join(errors))
    class a: pass
    a.phase, a.state, a.json = phase, state_path, as_json
    tickets = read_json(out(cfg, f'tickets/phase-{a.phase}.json'))
    path = a.state or f'state/phase-{int(phase)}.json'
    state = json.load(open(path)) if os.path.exists(path) else {}
    if cfg.get('artifact_version'):
        from . import events
        from .execution import merge_evidence
        merged = {e['ticket']: e for e in events.read(cfg,phase) if e['kind'] == 'merged'}
        for tid, event in merged.items():
            if merge_evidence(cfg,phase,tid,event.get('data',{})) != event['data'].get('evidence_sha256'):
                raise ValueError(f'{tid} merge evidence changed')
        unverified = {tid for tid, status in state.items() if status == 'merged'} - set(merged)
        if unverified: raise ValueError(f'merged state lacks verified events: {sorted(unverified)}')
        state.update({tid: 'merged' for tid in merged})
    now, later, held = eligible(tickets, state)
    if a.json:
        print(json.dumps({'claimable_now': [t['id'] for t in now],
                          'max_concurrency': len(now),
                          'claimable_later': [t['id'] for t in later],
                          'held': [{'id': i, 'reason': r} for i, r in held]}, indent=1))
        return 0
    if not now and not later and not held:
        print("  phase complete"); return 0
    if now:
        print(f"  claimable now ({len(now)}, all concurrent - disjoint file ownership):")
        for t in now:
            print(f"    {t['id']:6s} {t['kind']:<12s} {t['title']}")
    for i, r in held:
        print(f"    {i:6s} held        {r}")
    return 0


