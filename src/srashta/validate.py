#!/usr/bin/env python3
"""THE GATE. Exit non-zero on any error.

Conformance to this method means: this script passes. Not that an agent followed
prose. That is what makes the method portable across agents and harnesses.

Expect it to fail, and read every failure as a real defect. In the calibration run
it failed three times - wave/dependency contradictions, a file collision between two
concurrent tickets, then seven requirements no ticket implemented. A decomposition
that passes first time has not been tested.
"""
import fnmatch, hashlib, json, os, re, shutil, subprocess, sys, tempfile, yaml
from collections import defaultdict
from .common import load_project, out, read_json

def _glob_to_regex(g):
    """Translate a path glob to a regex, keeping ** / * / ? path-aware."""
    out, i = [], 0
    while i < len(g):
        c = g[i]
        if c == '*':
            if g[i:i+3] == '**/':  out.append(r'(?:[^/]+/)*'); i += 3; continue
            if g[i:i+2] == '**':   out.append(r'.*');          i += 2; continue
            out.append(r'[^/]*');  i += 1; continue
        if c == '?': out.append(r'[^/]'); i += 1; continue
        out.append(re.escape(c)); i += 1
    return re.compile('^' + ''.join(out) + '$')


def globs_intersect(a, b):
    """Do two path patterns share any concrete path? Returns a witness, or None.

    Pattern intersection is decidable but fiddly; constructing a witness is both
    simpler and far more useful in an error message. Substitute each pattern's
    literal segments into the other's wildcards and test both directions.
    """
    if a == b: return a
    ra, rb = _glob_to_regex(a), _glob_to_regex(b)
    if ra.match(b): return b
    if rb.match(a): return a
    for src, dst, rs, rd in ((a, b, ra, rb), (b, a, rb, ra)):
        seg_src, seg_dst = src.split('/'), dst.split('/')
        if len(seg_src) != len(seg_dst): continue
        cand = [d if ('*' in s or '?' in s) else s
                for s, d in zip(seg_src, seg_dst)]
        w = '/'.join(cand)
        if '*' not in w and '?' not in w and rs.match(w) and rd.match(w):
            return w
    return None


def _digest(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(65536), b''): h.update(c)
    return h.hexdigest()

def derived_drift(cfg):
    """Re-derive into a temp tree and compare. Only the deterministic stages -
    tickets and contracts are authored, not derived, so they are excluded."""
    from importlib import import_module
    src = cfg.get('out_dir', 'build')
    checked = ('requirements.json', 'requirements.assigned.json')
    present = [f for f in checked if os.path.exists(os.path.join(src, f))]
    if not present: return []
    with tempfile.TemporaryDirectory() as tmp:
        shadow = dict(cfg); shadow['out_dir'] = tmp
        import contextlib, io
        try:
            with contextlib.redirect_stdout(io.StringIO()):   # shadow run is silent
                import_module('.extract', package='srashta').main(shadow)
                import_module('.assign', package='srashta').main(shadow)
        except BaseException as e:
            # Swallowing this disabled the check exactly when it mattered: a broken
            # spec path plus a hand-edited artifact reported PASSED. An unverifiable
            # artifact is a defect, not an absence of one.
            return [(f, f"could not verify - regeneration failed: "
                        f"{type(e).__name__}: {str(e)[:120]}") for f in present]
        out = []
        for f in present:
            shadow_f = os.path.join(tmp, f)
            if not os.path.exists(shadow_f):
                out.append((f, "regeneration did not produce it"))
            elif _digest(os.path.join(src, f)) != _digest(shadow_f):
                out.append((f, "it was hand-edited"))
        return out

def approval_marker(cfg, phase, root='.'):
    """FR-CON-001/002: contracts are approved before decomposition, and the approval
    is a file. It was written, displayed by `status`, and read by no gate - so a phase
    shipped unapproved and nothing said a word."""
    d = cfg.get('contracts_dir', 'contracts')
    design = os.path.join(root, d, f'phase-{phase}.md')
    marker = os.path.join(root, d, f'phase-{phase}.approved')
    if not os.path.exists(design):
        return f"{design} does not exist - a phase is decomposed from its contracts"
    if not os.path.exists(marker):
        return (f"{marker} does not exist - the contract design has not been approved. "
                f"Every ticket in this phase inherits those decisions, which is why the "
                f"approval is a human gate. `touch {marker}` once you have read it.")
    return None


def check(cfg, phase):
    reqs = [r for r in read_json(out(cfg, 'requirements.assigned.json'))
            if str(r['phase']) == str(phase)]
    gate = approval_marker(cfg, phase)
    allreq = {r['id'] for r in read_json(out(cfg, 'requirements.assigned.json'))}
    tickets = read_json(out(cfg, f'tickets/phase-{phase}.json'))
    req_ids = {r['id'] for r in reqs}
    by_id = {t['id']: t for t in tickets}
    E, W = [], []
    if gate: E.append(gate)

    # 0 PHASE GATES. A phase may declare artifacts that must exist BEFORE it decomposes -
    #   the published API contract being the one that matters, since screens are designed
    #   against it. `status` reported these as unmet and then let the decomposition happen
    #   anyway, so the gate was advice. A gate nothing enforces is not a gate.
    ph = (cfg.get('phases') or {}).get(phase) or (cfg.get('phases') or {}).get(str(phase)) \
         or (cfg.get('phases') or {}).get(int(phase) if str(phase).isdigit() else phase) or {}
    for a in (ph.get('gate_artifacts') or []):
        if not os.path.exists(a):
            E.append(f"phase {phase} declares {a} as a gate artifact and it does not "
                     f"exist. Tickets written now would be written against a payload "
                     f"nobody has published.")

    # 0b LAYER ORDER. api before surface, project-wide. The whole method rests on the
    #    endpoints being settled before anything is drawn against them; a phase plan that
    #    puts a screen first is that rule broken at the only place it can still be cheap.
    order = sorted((cfg.get('phases') or {}).items(), key=lambda kv: str(kv[0]))
    first_surface = next((k for k, v in order if (v or {}).get('layer') == 'surface'), None)
    if first_surface is not None:
        late_api = [k for k, v in order
                    if (v or {}).get('layer') == 'api' and str(k) > str(first_surface)]
        if late_api:
            E.append(f"phase {first_surface} is a surface phase ordered before api "
                     f"phase(s) {', '.join(str(k) for k in late_api)}. Screens are "
                     f"composed against a published contract, so every api phase "
                     f"precedes every surface phase.")

    # 0c THE GRAPH MUST BE DERIVED, and this is checked FIRST because every check below
    #    reads a field finalise() writes. Checking it late meant an authored file raised
    #    KeyError from inside check 1 - a crash where a defect report belongs.
    from .waves import DERIVATION as _D
    _stamp = f'waves.finalise/{_D}'
    unstamped = [t['id'] for t in tickets if t.get('derived_by') != _stamp]
    if unstamped:
        E.append(f"{len(unstamped)} of {len(tickets)} ticket(s) were not produced by "
                 f"waves.finalise ({', '.join(unstamped[:6])}"
                 f"{'…' if len(unstamped) > 6 else ''}). Waves are derived from the "
                 f"dependency graph, never authored, and a file that skipped derivation "
                 f"also skipped cycle detection, blocker propagation and the edges that "
                 f"keep a shared resource uncontended. Run `srashta waves {phase}`, then "
                 f"validate again — nothing else here can be checked until you do.")
        return reqs, tickets, {}, defaultdict(list), defaultdict(list), E, W

    # C- tickets SUPPORT a requirement; exactly one T- ticket OWNS it; any ticket may ASSERT it.
    owners, seen = defaultdict(list), defaultdict(list)
    for t in tickets:
        for r in t['requirements']:
            seen[r].append(t['id'])
            if t['kind'] == 'feature': owners[r].append(t['id'])
        for r in t.get('asserts', []): seen[r].append(t['id'])

    # 1 coverage + single ownership
    for r in sorted(req_ids):
        o = owners.get(r, [])
        if not seen.get(r):
            E.append(f"{r} is cited by no ticket")
        elif len(o) > 1:
            E.append(f"{r} has {len(o)} feature owners {o} - exactly one is required")
        elif not o:
            E.append(f"{r} has no feature ticket that owns it (supported by {seen[r]})")

    # 2 citations resolve, and stay inside this phase
    for t in tickets:
        for r in t['requirements'] + t.get('asserts', []):
            if r.startswith(('FR-', 'NFR-')):
                if r not in allreq: E.append(f"{t['id']} cites unknown requirement {r}")
                elif r not in req_ids: E.append(f"{t['id']} cites {r}, assigned to another phase")

    # 3 exclusive file ownership within a wave.
    #   fnmatch in both directions catches literal-vs-glob and MISSES glob-vs-glob:
    #   'app/Models/*.php' and 'app/*/User.php' both own 'app/Models/User.php' while
    #   neither matches the other as a string. Every two-level path fits through that,
    #   and this is the single invariant the concurrency model rests on.
    by_wave = defaultdict(list)
    for t in tickets: by_wave[t['wave']].append(t)
    for wave, ts in sorted(by_wave.items()):
        for i, a in enumerate(ts):
            for b in ts[i+1:]:
                for pa in a['owned_files']:
                    for pb in b['owned_files']:
                        w = globs_intersect(pa, pb)
                        if w:
                            E.append(f"wave {wave}: {a['id']} and {b['id']} both own "
                                     f"{pa} / {pb} (e.g. {w}) - concurrent agents would collide")

    # 3b waves must be DERIVED. FR-DEC-001 says they are never authored, but nothing
    #    checked, and finalise() had no caller in the package - it was invoked by a
    #    markdown instruction to a planning agent. A tickets file that skipped it also
    #    skipped cycle detection and blocker propagation.
    from .waves import finalise as _finalise, DERIVATION as _DERIV
    if True:
        # Cheap and decisive: re-derive and compare.
        import copy
        shadow = copy.deepcopy(tickets)
        for x in shadow: x.pop('wave', None); x.pop('derived_by', None)
        try:
            redone, _, _ = _finalise(shadow, shared=cfg.get('shared_resources'))
            got = {x['id']: x['wave'] for x in redone}
            for t in tickets:
                if got.get(t['id']) != t['wave']:
                    E.append(f"{t['id']} claims wave {t['wave']} but the graph derives "
                             f"{got.get(t['id'])} - the file was edited after derivation")
        except SystemExit as e:
            E.append(f"waves cannot be re-derived: {e}")

    # 3c SHARED RESOURCES. Disjoint owned_files is not the same as no contention:
    #    three endpoint tickets with different files all need routes/api.php, and
    #    nothing above would see it. Declared resources are checked by strategy.
    shared = cfg.get('shared_resources') or {}
    for name, spec in sorted(shared.items()):
        pats = spec.get('paths') or []
        strategy = spec.get('strategy', 'serialise')
        for t in tickets:
            hits = [f for f in t['owned_files']
                    if any(globs_intersect(f, p) for p in pats)]
            declared = name in (t.get('touches') or [])
            if hits and not declared:
                E.append(f"{t['id']} owns {hits[0]}, part of shared resource '{name}', "
                         f"without declaring it in touches. Undeclared contention is "
                         f"invisible to every other check.")
            if not (hits or declared):
                continue
            if strategy == 'contract_only' and t['kind'] != 'contract':
                E.append(f"{t['id']} is a {t['kind']} ticket touching '{name}', which is "
                         f"contract-only. Shared structure belongs to a contract — a "
                         f"feature ticket changing it is already a contract violation.")
            if strategy == 'fragment':
                frag = (spec.get('fragment') or '').replace('{module}', t['module'])
                aggregate = [f for f in hits if not globs_intersect(f, frag)]
                if aggregate:
                    E.append(f"{t['id']} owns the aggregate {aggregate[0]} rather than its "
                             f"fragment. Own {frag} instead — the aggregate loads the "
                             f"fragments, so there is nothing to contend over.")
                elif declared and frag and not any(globs_intersect(f, frag)
                                                   for f in t['owned_files']):
                    W.append(f"{t['id']} declares '{name}' but owns no fragment ({frag})")
        if strategy == 'serialise':
            group = [t['id'] for t in tickets if name in (t.get('touches') or [])]
            if len(group) > 3:
                W.append(f"'{name}' serialises {len(group)} tickets into a chain "
                         f"{len(group)} waves deep. Correct, but this is the signal to "
                         f"fragment the resource instead — see strategy: fragment.")

    # 4 dependencies exist and point to strictly earlier waves
    for t in tickets:
        for d in t['depends_on']:
            if d not in by_id: E.append(f"{t['id']} depends on unknown ticket {d}")
            elif by_id[d]['wave'] >= t['wave']:
                E.append(f"{t['id']} (wave {t['wave']}) depends on {d} "
                         f"(wave {by_id[d]['wave']}) - not a strictly earlier wave")

    # 5 every non-contract ticket rests, transitively, on a frozen contract
    def reaches_contract(tid, path=frozenset()):
        if tid in path: return False
        for d in by_id[tid]['depends_on']:
            if d.startswith('C-') or reaches_contract(d, path | {tid}): return True
        return False
    for t in tickets:
        if t['kind'] != 'contract' and not reaches_contract(t['id']):
            E.append(f"{t['id']} rests on no frozen contract, directly or transitively - "
                     f"it will invent shared structure")

    # 6 verifiable, evidenced, scoped
    from .waves import BRIEF_FEEDBACK
    for t in tickets:
        if not t['acceptance_tests']: E.append(f"{t['id']} has no acceptance tests")
        if not t['evidence']:         E.append(f"{t['id']} produces no evidence")
        if not t['owned_files']:      E.append(f"{t['id']} owns no files")
        # Removing this is how pack quality stops being measurable.
        if BRIEF_FEEDBACK not in t['evidence']:
            E.append(f"{t['id']} does not require brief feedback as evidence. Every ticket "
                     f"closes by saying whether its brief was sufficient — that is the only "
                     f"reliable measure of whether the decomposition is producing good briefs.")

    # 7 blockers are declared, known, and propagated
    open_q = {k for k, v in cfg.get('open_questions', {}).items()
              if v.get('kind') == 'blocker' and not v.get('answered')}
    for t in tickets:
        for d in t['depends_on']:
            miss = set(by_id[d]['blocked_on']) - set(t['blocked_on'])
            if miss: E.append(f"{t['id']} depends on blocked {d} but does not inherit {sorted(miss)}")
        unknown = set(t['blocked_on']) - open_q
        if unknown: E.append(f"{t['id']} declares blocker(s) {sorted(unknown)} "
                             f"not open in project.yaml")

    # 8 DERIVED-INDEX PRINCIPLE: build/ is a view, not a source.
    #    Regenerate the deterministic artifacts from source and require them to match.
    #    If they differ, someone hand-edited a derived file - which means the next
    #    regeneration will silently discard their change.
    if not cfg.get('skip_derived_check'):
        for f, why in derived_drift(cfg):
            E.append(f"derived artifact {f}: {why}. It is a view, not a source - "
                     f"change the source and regenerate.")

    # 9 LAYER SEPARATION. Business logic is finished server-side before any screen
    #    exists, so the machine-verifiable work (endpoints: precise contracts, EARS
    #    criteria mapping 1:1 onto tests) is separated from the taste-dependent work
    #    (screens: layout, responsiveness, accessibility) that needs a human eye.
    layers = cfg.get('layers') or {}
    coupled = set(cfg.get('transport_coupled') or [])
    if layers:
        for t in tickets:
            lay = t.get('layer')
            if not lay:
                E.append(f"{t['id']} declares no layer; one of {sorted(layers)} or 'coupled'")
                continue
            if lay == 'coupled':
                # Real-time channels, uploads, OAuth redirects and canvas sync do not
                # decouple cleanly. They are EXEMPT BY DECLARATION, never by accident.
                if t['module'] not in coupled:
                    E.append(f"{t['id']} claims layer 'coupled' but module '{t['module']}' is "
                             f"not in transport_coupled: {sorted(coupled)}. Declare the "
                             f"exemption in project.yaml or split the ticket.")
                continue
            if lay not in layers:
                E.append(f"{t['id']} has unknown layer '{lay}'"); continue
            owns = layers[lay].get('owns') or []
            for f in t['owned_files']:
                if owns and not any(fnmatch.fnmatch(f, g) for g in owns):
                    E.append(f"{t['id']} is layer '{lay}' but owns {f}, which is outside "
                             f"that layer. A ticket that spans layers is the coupling this "
                             f"separation exists to prevent.")
            for c in layers[lay].get('requires_contracts') or []:
                if t['kind'] == 'feature' and c not in t['contracts_used']:
                    E.append(f"{t['id']} is layer '{lay}' and must rest on contract {c}")
            under = layers[lay].get('depends_on_layer')
            if under and t['kind'] == 'feature':
                def reaches_layer(tid, want, seen=frozenset()):
                    if tid in seen: return False
                    for d in by_id[tid]['depends_on']:
                        if by_id[d].get('layer') == want: return True
                        if reaches_layer(d, want, seen | {tid}): return True
                    return False
                if not reaches_layer(t['id'], under):
                    E.append(f"{t['id']} is layer '{lay}' but reaches no '{under}' ticket. "
                             f"A screen with no endpoint behind it is a screen built on a guess.")

    # 10 JOURNEY COVERAGE, both directions. Endpoints must fall out of what a user
    #    actually does, not out of the entity model - otherwise the API is complete
    #    and the screen still cannot be built.
    journeys = cfg.get('journeys') or {}
    if journeys:
        steps = {s['id'] for j in journeys.values() for s in (j.get('steps') or [])}
        served = defaultdict(list)
        for t in tickets:
            for sid in t.get('serves') or []:
                if sid not in steps:
                    E.append(f"{t['id']} serves unknown journey step {sid}")
                served[sid].append(t['id'])
        api_layer = next((k for k, v in layers.items() if not v.get('depends_on_layer')), 'api')
        for t in tickets:
            if t['kind'] == 'feature' and t.get('layer') == api_layer and not t.get('serves'):
                W.append(f"{t['id']} serves no journey step - is anything going to call it?")
        # A step may legitimately be served by a later phase, so this is advisory
        # until the last phase. Unknown references above are still hard errors.
        for sid in sorted(steps - set(served)):
            W.append(f"journey step {sid} is served by no ticket yet")

    # 11 THE API CONTRACT IS OWNED BY NOBODY. It is generated in CI from the routes.
    #    A ticket owning it would collide with every other api ticket in its wave -
    #    which is exactly the rule check 3 exists to enforce - and would make an agent
    #    responsible for remembering to document, which they do not reliably do.
    contract_paths = [a for ph in (cfg.get('phases') or {}).values()
                      for a in (ph.get('gate_artifacts') or [])]
    for t in tickets:
        for f in t['owned_files']:
            if f in contract_paths:
                E.append(f"{t['id']} owns {f}, the generated API contract. No ticket may "
                         f"own it: CI generates it from the routes, so concurrent tickets "
                         f"in a wave never collide over it.")

    # 12 events carry schemas; a listened event has a consumer contract
    ev = cfg.get('events', {})
    for name, spec in ev.items():
        if not spec.get('schema'):
            E.append(f"event {name} has no payload schema - prose freezes drift silently")
        if spec.get('listeners') and not spec.get('consumer_contracts'):
            E.append(f"event {name} has listeners {spec['listeners']} but no consumer contract")

    # warnings
    for t in tickets:
        n = len([r for r in t['requirements'] if r.startswith(('FR-', 'NFR-'))])
        if n > 12 and t['kind'] != 'contract':
            W.append(f"{t['id']} cites {n} requirements - consider splitting")
        if len(t['acceptance_tests']) > cfg.get('max_acceptance_tests', 12):
            W.append(f"{t['id']} has {len(t['acceptance_tests'])} acceptance tests - "
                     f"above the calibrated ceiling")
    return reqs, tickets, by_wave, owners, seen, E, W

def main(cfg, phase, quiet=False):
    reqs, tickets, by_wave, owners, seen, E, W = check(cfg, phase)
    covered = sum(1 for r in reqs if seen.get(r['id']))
    runnable = [t['id'] for t in tickets if not t['blocked_on']]
    blocked  = [t['id'] for t in tickets if t['blocked_on']]
    drift    = [t['id'] for t in tickets
                if t.get('wave_hint') is not None and t['wave_hint'] != t['wave']]
    if quiet:
        # Decision-shaped for the one-command runner. Full detail lives in build/run.log.
        if not E:
            print(f"  ✓ {'Validate ticket graph':<28} {len(tickets)} tickets, "
                  f"{len(by_wave)} waves, {len(runnable)} runnable now")
            for w in sorted(W)[:3]: print(f"  note: {w}")
            return 0
        print(f"  ✗ {'Validate ticket graph':<28} {len(E)} defect(s)")
        for e in E: print(f"      {e}")
        return 1
    print(f"Phase {phase} ticket graph validation")
    print(f"  requirements in phase : {len(reqs)}")
    print(f"  covered by a ticket   : {covered} ({covered*100//max(len(reqs),1)}%)")
    print(f"  tickets               : {len(tickets)} across {len(by_wave)} waves")
    print(f"  contract tickets      : {sum(1 for t in tickets if t['kind']=='contract')}")
    print(f"  acceptance tests      : {sum(len(t['acceptance_tests']) for t in tickets)}")
    print(f"  runnable now          : {len(runnable)}")
    print(f"  blocked on an open Q  : {len(blocked)}" + (f" -> {blocked}" if blocked else ""))
    if drift: print(f"  waves corrected by the graph : {len(drift)} of {len(tickets)}")
    print()
    for w in sorted(W): print("  WARN ", w)
    if W: print()
    if E:
        print(f"FAILED — {len(E)} error(s):")
        for e in E: print("  ERROR", e)
        return 1
    print("PASSED — no errors.")
    return 0

