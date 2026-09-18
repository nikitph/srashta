#!/usr/bin/env python3
"""Step 6c - emit one bounded context pack per ticket.

An agent receives ONLY its pack, never the spec. This is information hiding applied
to the context window: a human engineer can be handed the whole spec because they
look up what they need and ignore the rest; an agent drifts toward whatever else is there.

Packs are plain Markdown, so any agent in any harness consumes them unchanged.
"""
import os, sys, yaml
from .common import load_project, out, read_json

def prior_attempts(cfg, phase, ticket_id):
    """What the last attempt on this ticket hit.

    The event log already holds it; the pack simply did not render it, so a retrying
    agent rediscovered the same failure from scratch. Externalising this is the whole
    point of an append-only log - the memory is the artifact, not the agent."""
    from . import events
    # Swallowing this dropped the retry history of EVERY brief in the phase, silently,
    # on one truncated line - which is the failure FR-BRF-002 exists to prevent.
    try:
        ev = [e for e in events.read(cfg, phase) if e['ticket'] == ticket_id]
    except Exception as e:
        raise SystemExit(
            f"ERROR: the events log for phase {phase} could not be read "
            f"({type(e).__name__}: {e}). Briefs would silently lose their retry "
            f"history, so nothing is written. Repair {events.path(cfg, phase)} first.")
    if not ev: return None
    attempts = sum(1 for e in ev if e['kind'] == 'attempt_started')
    if attempts < 1: return None
    failed, oos, cc = [], [], False
    for e in ev:
        d = e.get('data') or {}
        if e['kind'] == 'tests_failed':       failed += d.get('tests', [])
        if e['kind'] == 'out_of_scope_touch': oos += d.get('files', [])
        if e['kind'] == 'contract_change_filed': cc = True
        if e['kind'] == 'merged':             return None      # done; nothing to carry
    if not (failed or oos or cc): return None
    return {'attempts': attempts, 'failed': failed, 'out_of_scope': oos, 'contract': cc}


def render(t, reqs, cfg, constitution, glossary, defaults, by_id, history=None):
    ids = t['requirements'] + t.get('asserts', [])
    lay = t.get('layer')
    L = [f"# {t['id']} — {t['title']}", '',
         f"**Module:** `{t['module']}`  **Kind:** {t['kind']}"
         + (f"  **Layer:** {lay}" if lay else '')
         + f"  **Wave:** {t['wave']}  "
         f"**Depends on:** {', '.join(t['depends_on']) or 'nothing'}", '']
    if lay == 'api':
        L += ['> **Server-side only.** Build the behaviour and its endpoint. Do not create, '
              'reference or reason about any screen — a separate ticket does that against '
              'the contract you publish here. Put no business logic in the controller: it '
              'calls the action and wraps the response, nothing more.', '']
    elif lay == 'surface':
        L += ['> **Screen only.** The endpoints you consume and the design tokens you use are '
              'both already frozen, so you are composing, not deciding. If an endpoint does '
              'not return what this screen needs, STOP and file a contract-change ticket '
              'rather than reaching into the server.', '']
    steps = t.get('serves') or []
    if steps:
        jl = cfg.get('journeys') or {}
        by_step = {s['id']: s.get('text', '') for j in jl.values() for s in (j.get('steps') or [])}
        L += ['## What a person is doing when this runs', '']
        L += [f"- **{s}** {by_step.get(s, '')}" for s in steps] + ['']
    if t['blocked_on']:
        L += [f"> **BLOCKED — do not start.** Waiting on {', '.join(t['blocked_on'])}. "
              "A human must answer this before any code is written.", '']
    L += ['## Constitution (applies to every ticket)', '', '```', constitution.strip(), '```', '']
    L += ['## Requirements this ticket OWNS' if t['kind'] != 'contract'
          else '## Requirements this ticket SUPPORTS', '']
    for r in t['requirements']:
        rq = reqs.get(r)
        L.append(f"- **{r}** [{rq['priority']}] {rq['text']}" if rq else f"- **{r}**")
        for c in (rq or {}).get('criteria', []) or []:
            L.append(f"    - {c}")
    if t.get('asserts'):
        L += ['', '## Requirements this ticket VERIFIES but does not own', '']
        for r in t['asserts']:
            rq = reqs.get(r)
            if rq: L.append(f"- **{r}** [{rq['priority']}] {rq['text']}")
    doms = sorted({reqs[r]['domain'] for r in ids if r in reqs})
    gl = [f"- {d}: {glossary[d]}" for d in doms if d in glossary]
    if gl: L += ['', '## Domain rules that apply here', ''] + gl
    L += ['', '## Frozen contracts you may use and must not change', '']
    if t['contracts_used']:
        for c in t['contracts_used']:
            ct = by_id.get(c)
            if ct: L.append(f"- `{c}` {ct['title']} — files: {', '.join(ct['owned_files'])}")
        L += ['', 'If you need a contract change, STOP and file a contract-change ticket. '
              'Never alter a frozen contract from a feature ticket.']
    else:
        L.append('None — this ticket defines a contract. Everything it produces is frozen '
                 'once approved.')
    L += ['', '## Files this ticket owns exclusively', ''] + [f"- `{f}`" for f in t['owned_files']]
    L += ['', 'No other ticket in this wave may touch these paths, and this ticket may touch '
          'no others.', '']
    sh = t.get('touches') or []
    if sh:
        L += ['## Shared resources this ticket touches', '']
        for name in sh:
            spec = (cfg.get('shared_resources') or {}).get(name, {})
            strat = spec.get('strategy', 'serialise')
            if strat == 'fragment':
                frag = (spec.get('fragment') or '').replace('{module}', t['module'])
                L.append(f"- **{name}** — write only `{frag}`, never the aggregate. "
                         f"The aggregate loads the fragments.")
            elif strat == 'contract_only':
                L.append(f"- **{name}** — owned by a contract. Do not change it here; "
                         f"file a contract-change ticket.")
            else:
                L.append(f"- **{name}** — shared and serialised. The graph already "
                         f"orders you against the other tickets that touch it, so you "
                         f"have it to yourself. Keep your change minimal.")
        L.append('')
    L += ['## Configuration you must read, never hardcode', '', '```yaml']
    sects, n = cfg.get('config_for_domain', {}), 0
    seen = []
    for d in doms:
        for s in sects.get(d, []):
            if s not in seen: seen.append(s)
    for s in seen:
        for k, v in (defaults.get(s) or {}).items():
            L.append(f"{s}.{k}: {v}"); n += 1
    if not n: L.append('# none — this ticket reads no configured parameter')
    L += ['```', '']
    if history:
        L += [f"## What the previous attempt hit  (attempt {history['attempts'] + 1})", '']
        if history['failed']:
            L += ['These acceptance tests failed last time. Read them before writing code:', '']
            L += [f"- {x}" for x in dict.fromkeys(history['failed'])] + ['']
        if history['out_of_scope']:
            L += ['The last attempt modified files this ticket does not own. Do not repeat '
                  'that — if the work genuinely needs them, the ownership is wrong and that '
                  'is a decomposition defect worth reporting:', '']
            L += [f"- `{x}`" for x in dict.fromkeys(history['out_of_scope'])] + ['']
        if history['contract']:
            L += ['A contract-change ticket was filed against this work. Do not proceed '
                  'until it is resolved.', '']
    mine = [d for d in (cfg.get('decisions') or {}).values()
            if set(d.get('constrains') or []) & set(ids + [t['module']])]
    if mine:
        L += ['## Decisions already made — do not re-litigate these', '']
        for d in mine:
            L.append(f"- **{d['decision']}**")
            if d.get('rejected'):
                L.append(f"    Rejected: {d['rejected']}")
        L += ['', 'These were settled deliberately. If one looks wrong from inside this '
              'ticket, say so in the pull request — do not quietly implement the '
              'alternative.', '']
    L += ['## Acceptance tests — done means all of these pass', '']
    L += [f"{i+1}. {a}" for i, a in enumerate(t['acceptance_tests'])]
    L += ['', '## Evidence to attach to the pull request', ''] + [f"- {e}" for e in t['evidence']]
    L += ['', 'The last item is required of every ticket. Answer it honestly — "sufficient, '
          'but I had to infer the retention period" is the most useful answer there is, and '
          'the one that gets the next brief fixed.', '']
    L += ['## If this brief is missing something', '',
          'Do not read the specification and do not go looking in other parts of the '
          'repository. That is scope, not constraint, and reading it is how a ticket '
          'starts building things nobody asked for.', '',
          'Most of the time you will not need this — say what you inferred in the evidence '
          'above and carry on. Use this only when the ticket genuinely cannot proceed:', '',
          f"```bash\nsrashta event {t['id']} pack_insufficient "
          f"--data '{{\"needed\": \"…\"}}'\n```", '',
          'A brief that was missing something is a defect in the decomposition, not in '
          'you. Saying so is how it gets fixed — and if several tickets need the same '
          'thing, it goes into the template rather than being looked up each time.']
    if t.get('notes'): L += ['', '## Note', '', t['notes']]
    return '\n'.join(L) + '\n'

def main(cfg, phase):
    from .validate import approval_marker
    gate = approval_marker(cfg, phase)
    if gate:
        raise SystemExit(f"ERROR: {gate}")
    reqs = {r['id']: r for r in read_json(out(cfg, 'requirements.assigned.json'))}
    tickets = read_json(out(cfg, f'tickets/phase-{phase}.json'))
    by_id = {t['id']: t for t in tickets}
    constitution = open(cfg.get('constitution', 'constitution.md')).read()
    glossary = cfg.get('glossary', {})
    dpath = cfg.get('defaults', 'config/defaults.yaml')
    defaults = yaml.safe_load(open(dpath)) if os.path.exists(dpath) else {}
    d = out(cfg, f'context-packs/phase-{phase}'); os.makedirs(d, exist_ok=True)
    sizes = []
    carried = 0
    for t in tickets:
        hist = prior_attempts(cfg, phase, t['id'])
        if hist: carried += 1
        body = render(t, reqs, cfg, constitution, glossary, defaults, by_id, hist)
        open(os.path.join(d, f"{t['id']}.md"), 'w').write(body)
        sizes.append(len(body))
    spec = os.path.getsize(cfg['spec']['path'])
    mean = sum(sizes) // len(sizes)
    print(f"{len(sizes)} context packs -> {d}")
    print(f"  mean {mean} chars (~{mean//4} tokens), max {max(sizes)}")
    print(f"  spec is ~{spec//4} tokens — a pack is {spec//mean}x smaller")
    if carried:
        print(f"  {carried} pack(s) carry what a previous attempt hit")


