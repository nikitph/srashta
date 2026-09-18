#!/usr/bin/env python3
"""Step 6c - derive waves, propagate blockers, normalise tickets.

Waves are the longest dependency path to a root. NEVER hand-assigned: in a
calibration run on a 43-ticket phase, 30 tickets were authored into the wrong wave.
`srashta waves <phase>` runs it over an authored ticket graph in place.
"""
import os

KIND = {'C': 'contract', 'T': 'feature', 'I': 'integration'}
DERIVATION = 1          # bump when the derivation changes meaningfully

# Every ticket closes by answering this. It is injected here rather than authored,
# because a required item nobody has to remember is the only kind that survives.
#
# It rides on evidence deliberately. Asking an agent to NOTICE it lacks something and
# fire an event asks for calibrated uncertainty, which is what models are worst at -
# the default on missing information is to infer plausibly and continue. A question it
# must answer to close the ticket is answered; an action it must remember is not.
#
# It also catches the case no agent would ever volunteer separately, and the most
# useful one: "sufficient, but I had to infer X".
BRIEF_FEEDBACK = ("a one-line statement of whether this brief was sufficient, naming "
                  "anything you had to infer or could not find")

def _serialise_edges(tickets, shared):
    """Turn contention into explicit dependency edges, at plan time.

    Two tickets with disjoint owned_files still contend over bootstrap/app.php or a
    lockfile. Waiting for a lock at run time converts a planning failure into an
    invisible stall; an edge in the graph is reviewable, shows up in the wave numbers,
    and keeps the whole thing a DAG.

    Chaining is by ticket id so it is deterministic, and it respects existing edges:
    if B already depends on A, the chain runs A -> B, never the reverse.
    """
    added = []
    for name, spec in sorted((shared or {}).items()):
        if spec.get('strategy') != 'serialise':
            continue
        group = sorted(t['id'] for t in tickets if name in (t.get('touches') or []))
        if len(group) < 2:
            continue
        by_id = {t['id']: t for t in tickets}

        def reaches(a, b, seen=frozenset()):
            """Does a already depend on b, directly or transitively?"""
            if a in seen: return False
            for d in by_id[a]['depends_on']:
                if d == b or (d in by_id and reaches(d, b, seen | {a})): return True
            return False

        # order the group so existing dependencies are never inverted
        order, remaining = [], list(group)
        while remaining:
            free = [x for x in remaining
                    if not any(reaches(x, y) for y in remaining if y != x)]
            if not free: free = [remaining[0]]        # defensive; cycle caught later
            pick = sorted(free)[0]
            order.append(pick); remaining.remove(pick)

        for prev, cur in zip(order, order[1:]):
            if not reaches(cur, prev):
                by_id[cur]['depends_on'] = list(by_id[cur]['depends_on']) + [prev]
                added.append((name, prev, cur))
    return added


def finalise(tickets, shared=None):
    validate_records(tickets)
    by_id = {t['id']: t for t in tickets}
    for t in tickets:
        t.setdefault('kind', KIND.get(t['id'][0], 'feature'))
        t.setdefault('asserts', [])
        t.setdefault('blocked_on', [])
        t.setdefault('layer', None)       # api | surface | coupled
        t.setdefault('serves', [])        # journey step ids this ticket makes possible
        t.setdefault('notes', None)
        t.setdefault('touches', [])
        t['contracts_used'] = [d for d in t['depends_on'] if d.startswith('C-')]
        if BRIEF_FEEDBACK not in t['evidence']:
            t['evidence'] = list(t['evidence']) + [BRIEF_FEEDBACK]
        t.setdefault('telemetry', {k: None for k in
            ('attempts','first_run_test_failures','contract_change_filed',
             'out_of_scope_files_touched','review_rounds','agent','diff_lines')})
        missing = [d for d in t['depends_on'] if d not in by_id]
        if missing: raise SystemExit(f"{t['id']} depends on unknown ticket(s) {missing}")

    # Contention becomes an edge BEFORE waves are derived, so the serialisation is
    # visible in the wave numbers rather than discovered by two agents at once.
    added = _serialise_edges(tickets, shared)
    for t in tickets:
        t['contracts_used'] = [d for d in t['depends_on'] if d.startswith('C-')]

    memo = {}
    def depth(i, seen=()):
        if i in memo: return memo[i]
        if i in seen: raise SystemExit(f"dependency cycle: {' -> '.join(seen + (i,))}")
        d = max([depth(p, seen + (i,)) + 1 for p in by_id[i]['depends_on']] or [0])
        memo[i] = d
        return d
    for t in tickets:
        t.setdefault('wave_hint', None)
        t['wave'] = depth(t['id'])
        # A stamp proving these waves came from the graph. Without it a hand-written
        # tickets file skips cycle detection, blocker propagation and the drift report
        # entirely - and validate read t['wave'] as given, so nothing noticed.
        t['derived_by'] = f'waves.finalise/{DERIVATION}'

    changed = True                      # blockers propagate along dependency edges
    while changed:
        changed = False
        for t in tickets:
            inherited = {b for p in t['depends_on'] for b in by_id[p]['blocked_on']}
            new = sorted(set(t['blocked_on']) | inherited)
            if new != t['blocked_on']:
                t['blocked_on'] = new; changed = True

    def contracts(tid, visited=None):
        visited = set() if visited is None else visited
        if tid in visited: return set()
        visited.add(tid)
        result = set()
        for dependency in by_id[tid]['depends_on']:
            if by_id[dependency]['kind'] == 'contract': result.add(dependency)
            result.update(contracts(dependency, visited))
        return result
    for ticket in tickets:
        ticket['contracts_used'] = sorted(contracts(ticket['id']))
    tickets.sort(key=lambda x: (x['wave'], x['id']))
    drift = [(t['id'], t['wave_hint'], t['wave'])
             for t in tickets if t['wave_hint'] is not None and t['wave_hint'] != t['wave']]
    return tickets, drift, added


def main(cfg, phase):
    """`srashta waves N` — derive waves over the authored ticket graph, in place.

    finalise() is the only thing that may produce a ticket graph, and once the validator
    started enforcing that (it rejects an unstamped file), nothing in the CLI could
    produce one: a planning agent authored tickets and validation refused them with no
    way forward. A rule with no command behind it is a trap, not a gate.

    Authoring is dependencies, ownership and tests. Waves, contracts_used, blocker
    propagation and the edges that serialise a shared resource are derived here.
    """
    import json
    from .common import out
    p = out(cfg, f'tickets/phase-{phase}.json')
    if cfg.get('artifact_version'):
        from .tickets import write
        tickets, drift, added = write(cfg, phase)
        n_before = len(tickets)
    else:
        # Programmatic 0.1.x compatibility. The CLI upgrade preserves these as source.
        if not os.path.exists(p):
            raise SystemExit(f'ERROR: {p} does not exist; author tickets first')
        tickets = json.load(open(p))
        n_before = len(tickets)
        tickets, drift, added = finalise(tickets, shared=cfg.get('shared_resources'))
        from .common import write_json
        write_json(p, tickets)

    waves = {}
    for t in tickets: waves.setdefault(t['wave'], []).append(t['id'])
    print(f"  {n_before} tickets -> {len(waves)} waves  ({p})")
    for w in sorted(waves):
        print(f"    wave {w}: {len(waves[w]):3d}  {', '.join(waves[w][:6])}"
              f"{'…' if len(waves[w]) > 6 else ''}")
    if added:
        print(f"\n  {len(added)} edge(s) added so a shared resource is never contended:")
        for name, prev, cur in added:
            print(f"    {cur} now depends on {prev}  (both touch '{name}')")
        print(f"  Ordering costs a wave. If this list is long, fragment the resource "
              f"instead.")
    if drift:
        print(f"\n  {len(drift)} authored wave(s) disagreed with the graph and were "
              f"corrected:")
        for tid, hint, got in drift[:10]:
            print(f"    {tid}: authored {hint}, derived {got}")
        if len(drift) > 10: print(f"    … and {len(drift) - 10} more")
        print(f"  A hint is a hint. The dependencies are what run.")
    print(f"\n  next: srashta packs {phase} && srashta validate {phase}")
    return 0


def validate_records(tickets):
    import re
    from .paths import validate_pattern
    if not isinstance(tickets, list) or not tickets:
        raise SystemExit('ERROR: ticket graph must be a nonempty array')
    seen = set()
    for ticket in tickets:
        if not isinstance(ticket, dict): raise SystemExit('ERROR: ticket must be an object')
        tid = ticket.get('id')
        if not isinstance(tid, str) or not re.fullmatch(r'[CTI]-[0-9]{2,3}[a-z]?', tid):
            raise SystemExit(f'ERROR: invalid ticket id {tid!r}')
        if tid in seen: raise SystemExit(f'ERROR: duplicate ticket id {tid}')
        seen.add(tid)
        for key in ('title', 'module'):
            if not isinstance(ticket.get(key), str) or not ticket[key].strip():
                raise SystemExit(f'ERROR: {tid}: {key} must be nonempty text')
        for key in ('depends_on', 'owned_files', 'requirements', 'acceptance_tests', 'evidence'):
            if not isinstance(ticket.get(key), list) or any(not isinstance(x, str) or not x.strip() for x in ticket[key]):
                raise SystemExit(f'ERROR: {tid}: {key} must be an array of nonempty strings')
        for pattern in ticket['owned_files']: validate_pattern(pattern)
        for key in ('blocked_on', 'asserts', 'touches', 'serves'):
            if key in ticket and (not isinstance(ticket[key], list) or any(not isinstance(x, str) for x in ticket[key])):
                raise SystemExit(f'ERROR: {tid}: invalid {key}')
        if ticket.get('kind', KIND[tid[0]]) != KIND[tid[0]]:
            raise SystemExit(f'ERROR: {tid}: kind disagrees with identifier')
