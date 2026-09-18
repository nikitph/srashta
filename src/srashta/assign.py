#!/usr/bin/env python3
"""Step 5 - assign every requirement to exactly one module and one phase.

Two reviewable layers: domain defaults from project.yaml, and per-id overrides
that must each carry a reason. Totality is asserted, not hoped for.
"""
import sys
from collections import Counter
from .common import load_project, out, read_json, write_json, die

def main(cfg):
    reqs = read_json(out(cfg, 'requirements.json'))
    dom2mod = {}
    for module, domains in cfg['modules'].items():
        for domain in domains:
            if domain in dom2mod: die(f'domain {domain} is assigned to multiple modules')
            dom2mod[domain] = module
    dom2phase, pname = {}, {}
    for p, spec in cfg['phases'].items():
        pname[int(p)] = spec['name']
        for d in spec.get('domains', []):
            if d in dom2phase: die(f'domain {d} is assigned to multiple phases')
            dom2phase[d] = int(p)

    unknown = sorted({r['domain'] for r in reqs} - set(dom2mod))
    if unknown: die(f"domains with no module in project.yaml: {unknown}")
    unphased = sorted({r['domain'] for r in reqs} - set(dom2phase))
    if unphased:
        die(f"domains named in no phase: {unphased}. A domain in no phase is orphaned by any "
            f"phase-driven decomposition - fix the phase plan or the spec.")

    unknown_overrides = set(cfg.get('overrides', {})) - {r['id'] for r in reqs}
    if unknown_overrides: die(f'overrides name unknown requirements: {sorted(unknown_overrides)}')
    for r in reqs:
        r['module'] = dom2mod[r['domain']]
        ov = cfg['overrides'].get(r['id'])
        if ov:
            if not str(ov.get('reason', '')).strip(): die(f"override for {r['id']} has no reason")
            r['phase'], r['phase_reason'] = int(ov.get('phase', dom2phase[r['domain']])), ov['reason']
            if 'module' in ov:
                if ov['module'] not in cfg['modules']: die(f'unknown override module {ov["module"]}')
                r['module'] = ov['module']
        else:
            r['phase'], r['phase_reason'] = dom2phase[r['domain']], f"domain default ({r['domain']})"
        if r['phase'] not in pname: die(f'unknown override phase {r["phase"]}')
        r['phase_name'] = pname[r['phase']]

    assert all(r.get('phase') is not None and r.get('module') for r in reqs)
    p = out(cfg, 'requirements.assigned.json'); write_json(p, reqs)
    c = Counter(r['phase'] for r in reqs)
    print(f"assigned {len(reqs)} requirements -> {p}")
    print(f"{'phase':<6}{'name':<28}{'reqs':>5}{'P0':>5}")
    for ph in sorted(c):
        p0 = sum(1 for r in reqs if r['phase'] == ph and r['priority'] == 'P0')
        print(f"{ph:<6}{pname[ph]:<28}{c[ph]:>5}{p0:>5}")
    print(f"overrides applied: {sum(1 for r in reqs if r['id'] in cfg['overrides'])}")
    return reqs

