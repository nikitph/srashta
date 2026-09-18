#!/usr/bin/env python3
"""Where is this project, and whose turn is it?

The repo is the handoff medium. Every Claude session starts fresh, so the repo -
not a conversation - carries the state. This reads the artifacts actually present
and says what happens next and who does it.

Run it at the start of any session, by any agent, or by a person.
"""
import glob, json, os, sys, yaml

def exists(p): return os.path.exists(p)

def _detect(root='.'):
    j = lambda *a: os.path.join(root, *a)
    cfg = yaml.safe_load(open(j('project.yaml'))) if exists(j('project.yaml')) else {}
    out_dir = cfg.get('out_dir', 'build')
    b = lambda *a: j(out_dir, *a)
    st = {
        'project':     cfg.get('project'),
        'api_frozen': exists(j('docs', '.openapi-frozen')),
        'repo':        exists(j('.git')),
        # files beginning with _ are templates shipped by init, not a spec
        'spec':        any(not os.path.basename(f).startswith('_')
                           for f in glob.glob(j('spec', '*'))),
        'brand':       exists(j('brand.yaml')),
        'design_sys':  exists(j('DESIGN.md')),
        'parsed':      exists(b('requirements.json')),
        'assigned':    exists(b('requirements.assigned.json')),
        'phases':      {},
        'blockers':    {k: v for k, v in (cfg.get('open_questions') or {}).items()
                        if v.get('kind') == 'blocker' and not v.get('answered')},
    }
    from .approvals import problem
    from .phase import closed
    for p in sorted(cfg.get('phases', {}), key=int):
        spec = cfg['phases'][p] if p in cfg['phases'] else cfg['phases'][str(p)]
        p = int(p)
        st['phases'][p] = {
            'layer': spec.get('layer', 'api'),
            'gate_artifacts': spec.get('gate_artifacts') or [],
            'contracts':   exists(j('contracts', f'phase-{p}.md')),
            'approved':    problem(cfg, p, root) is None,
            'tickets':     exists(b('tickets', f'phase-{p}.json')),
            'packs':       os.path.isdir(b('context-packs', f'phase-{p}')),
            'handoff':     os.path.isdir(b('handoff', f'phase-{p}')),
            'retro':       exists(j('retrospectives', f'phase-{p}.md')),
        }
        ticket_file = b('tickets', f'phase-{p}.json')
        ticket_ids = {t['id'] for t in json.load(open(ticket_file))} if exists(ticket_file) else set()
        state_file = j('state', f'phase-{p}.json') if cfg.get('artifact_version') else j('state.json')
        phase_state = json.load(open(state_file)) if exists(state_file) else {}
        from . import events
        merged_ids = {k for k,v in events.derive(events.read(cfg, p)).items() if v['merged']} if cfg.get('artifact_version') else {k for k,v in phase_state.items() if v == 'merged'}
        st['phases'][p].update(total=len(ticket_ids), merged=len(ticket_ids & merged_ids),
            closed=closed(cfg,p) if cfg.get('artifact_version') else st['phases'][p]['retro'])
        st['phases'][p]['gate_met'] = all(
            exists(j(a)) for a in st['phases'][p]['gate_artifacts'])
    st['exec'] = json.load(open(j('state.json'))) if exists(j('state.json')) else {}
    return cfg, st

def next_action(cfg, st):
    """Returns (who, what). 'you' = the human. 'claude' = a planning session.
       'orchestrator' = Multica or equivalent.

    Backend first. Brand and the design system are NOT asked for up front - they are
    asked for at the api -> surface boundary, once the endpoints exist. By then the
    published API contract is the input to whatever draws the screens, so the design
    is made against what actually exists rather than against an imagined payload."""
    if not st['repo']:      return 'claude', 'initialise the project repo (srashta init)'
    if not st['spec']:      return 'claude', 'author the spec  →  /spec-authoring'
    if not st['parsed'] or not st['assigned']:
        return 'claude', 'run the readiness audit and phase plan  →  /spec-readiness'
    gating = [k for k, v in st['blockers'].items() if v.get('gates_phase') == 0]
    if gating:
        owners = sorted({st['blockers'][k].get('owner', '?') for k in gating})
        return 'you', f"answer {', '.join(gating)} ({', '.join(owners)}), then set answered: true"
    for p, ph in sorted(st['phases'].items()):
        if ph['closed']: continue
        gating = [k for k,v in st['blockers'].items() if str(v.get('gates_phase')) == str(p)]
        if gating: return 'you', f"answer {', '.join(gating)} before phase {p}"
        # The api -> surface boundary. Everything server-side is done; now, and only
        # now, the look and feel gets attention - with the API contract in hand.
        if ph['layer'] == 'surface':
            if not st['brand']:
                return 'claude', ('endpoints are done — settle brand identity  →  '
                                  '/brand-identity')
            if not st['design_sys']:
                return 'claude', ('build the design system as C-00  →  '
                                  '/design-system-bootstrap')
            missing = ph['gate_artifacts'] if not ph['gate_met'] else []
            if missing:
                return 'you', (f'publish the API contract before drawing screens: '
                               f'{", ".join(missing)} — it is what the design is made '
                               f'against, and what generates the MCP server')
        if not ph['contracts']:
            return 'claude', f'design phase {p} contracts  →  /phase-decomposition'
        if not ph['approved']:
            return 'you', (f'review contracts/phase-{p}.md, then '
                           f'`srashta approve {p} --by NAME`')
        if not ph['tickets']:
            return 'claude', f'decompose phase {p} into tickets  →  /phase-decomposition'
        if not ph['handoff']:
            return 'claude', f'export the handoff  →  srashta export {p}'
        merged, total = ph['merged'], ph['total']
        if merged < total:
            return 'orchestrator', (f'phase {p}: {merged}/{total} tickets merged  '
                                    f'(srashta eligible {p})')
        if ph['retro'] and cfg.get('artifact_version'):
            return 'you', f'check and close phase {p}: srashta close {p} --by NAME'
        return 'claude', f'run the phase {p} retrospective  →  /build-retrospective'
    if cfg.get('artifact_version') and not st.get('api_frozen'):
        return 'you', 'freeze the verified API: srashta api freeze --by NAME'
    return 'you', 'all phases complete'

def main_cli():
    root = sys.argv[2] if len(sys.argv) > 2 else '.'
    cfg, st = detect(root)
    print(f"\n  {st['project'] or '(not initialised)'}\n")
    line = lambda ok, label: print(f"  {'✓' if ok else '·'} {label}")
    line(st['repo'], 'repo')
    line(st['spec'], 'spec')
    line(st['brand'], 'brand identity')
    line(st['assigned'], 'phases assigned')
    line(st['design_sys'], 'design system')
    for p, ph in sorted(st['phases'].items()):
        flags = {k: v for k, v in ph.items()
                 if k not in ('layer', 'gate_artifacts', 'gate_met', 'total', 'merged')}
        if not any(flags.values()): continue
        done = [k for k, v in flags.items() if v]
        print(f"  · phase {p} [{ph['layer']}]: {', '.join(done)}")
    who, what = next_action(cfg, st)
    label = {'you': 'YOUR TURN', 'claude': 'next planning session',
             'orchestrator': 'running'}[who]
    print(f"\n  {label}: {what}\n")
    return 0




def detect(root='.'):
    previous = os.getcwd()
    try:
        os.chdir(root)
        return _detect('.')
    finally:
        os.chdir(previous)
