#!/usr/bin/env python3
"""ONE COMMAND. Runs the chain, degrades rather than blocking, reports decisions.

Design rule for this file and every script it calls: internal mechanics never reach
the operator. No weights, no thresholds, no tuning knobs surfaced mid-flow. If a step
cannot do its job well, it falls back to something simpler and says so in one line.

The only things that stop the run are the human gates, and they stop it by design.

  srashta run             # everything up to the first gate
  srashta run --phase 0   # including the phase-0 ticket gate
  srashta run --verbose   # mechanics, for when something is actually wrong
"""
import argparse, io, os, sys, contextlib
from .common import load_project, out

STEPS = [
    ('extract',  'Parse the spec',            'extract'),
    ('lint',     'Check spec quality',        'lint'),
    ('dsm',      'Derive modules and flows',  'dsm'),
    ('assign',   'Assign phases',             'assign'),
]

def run_step(mod, cfg, verbose):
    buf = io.StringIO()
    try:
        from importlib import import_module
        m = import_module(f'.{mod}', package='srashta')
        with contextlib.redirect_stdout(buf):
            r = m.main(cfg)
        # A stage that RETURNS non-zero is a stage that failed. Only treating a raised
        # SystemExit as failure printed a checkmark beside "1 to fix" and carried on.
        return (r in (0, None) or not isinstance(r, int)), r, buf.getvalue()
    except SystemExit as e:
        return (e.code in (0, None)), None, buf.getvalue() + str(e)
    except Exception as e:
        return False, None, buf.getvalue() + f"{type(e).__name__}: {e}"

def run(cfg, phase=None, verbose=False):
    class a: pass
    a.phase, a.verbose = phase, verbose
    os.makedirs(cfg.get('out_dir', 'build'), exist_ok=True)
    log = open(out(cfg, 'run.log'), 'w')
    notes = []

    print(f"\n  {cfg['project']}\n")
    for key, label, mod in STEPS:
        ok, res, text = run_step(mod, cfg, a.verbose)
        log.write(f"\n===== {key} =====\n{text}\n")
        if a.verbose: print(text)
        if not ok:
            # A hard stop only where continuing would silently corrupt everything after it.
            print(f"  ✗ {label}")
            print(f"\n  Stopped: {key} cannot produce a usable result.")
            print(f"  {text.strip().splitlines()[-1] if text.strip() else ''}")
            print(f"\n  Detail: {out(cfg, 'run.log')}")
            return 1
        if key == 'extract':
            print(f"  ✓ {label:<28} {len(res)} requirements")
        elif key == 'lint':
            n = sum(1 for line in text.splitlines() if 'smells:' in line)
            hard = [l for l in text.splitlines() if l.strip().startswith('ERROR')]
            print(f"  ✓ {label:<28} " + ('clean' if not hard else f"{len(hard)} to fix"))
            if 'no EARS acceptance criteria' in text:
                notes.append("Spec has no EARS acceptance criteria, so ticket tests will be "
                             "inferred from prose rather than derived. Adding them is "
                             "transcription, not rethinking.")
        elif key == 'dsm':
            print(f"  ✓ {label:<28} {len(res['modules'])} modules, "
                  f"{len(res['cross_module_flows'])} flows need contracts")
            if res['llm_review_needed']:
                notes.append("Module grouping fell back to domain prefixes; the flow list is "
                             "for reading. No action needed from you.")
        elif key == 'assign':
            from collections import Counter
            c = Counter(r['phase'] for r in res)
            print(f"  ✓ {label:<28} {len(res)} requirements across {len(c)} phases")

    blockers = {k: v for k, v in cfg.get('open_questions', {}).items()
                if v.get('kind') == 'blocker' and not v.get('answered')}
    if a.phase is not None:
        tp = out(cfg, f'tickets/phase-{a.phase}.json')
        if not os.path.exists(tp):
            print(f"\n  Next: contracts and tickets for phase {a.phase} are not written yet.")
        else:
            from . import packs, validate
            with contextlib.redirect_stdout(io.StringIO()) as b:
                packs.main(cfg, a.phase)
            log.write(f"\n===== packs =====\n{b.getvalue()}\n")
            print(f"  ✓ {'Write agent briefs':<28} "
                  f"{b.getvalue().split()[0] if b.getvalue() else '?'} context packs")
            code = validate.main(cfg, a.phase, quiet=not a.verbose)
            if code:
                print(f"\n  Ticket graph is not valid yet. Each error above is a real defect.")
                return 1

    print()
    for n in notes: print(f"  note: {n}")
    gating = [k for k, v in blockers.items() if v.get('gates_phase') == 0]
    if gating:
        print(f"\n  Waiting on you: {', '.join(gating)} "
              f"({', '.join(sorted({blockers[k]['owner'] for k in gating}))})")
        print(f"  Everything else proceeds on recorded defaults.")
    print(f"\n  Detail if you want it: {out(cfg, 'run.log')}\n")
    return 0


