#!/usr/bin/env python3
"""Emit the run manifest and tracker-neutral ticket records.

The pipeline is BUILD TIME. The orchestrator is RUN TIME. They meet at exactly two
files and nothing else:

  out : build/handoff/phase-N/manifest.json + tickets.json + packs/
  in  : telemetry written back per ticket

Any orchestrator is integrated by mapping those two. Nothing else about this method
assumes a particular harness.
"""
import argparse, json, os, shutil, sys
from .common import load_project, out, read_json, write_json

def run(cfg, phase, repo=None, fmt='generic'):
    from .packs import build
    from .approvals import digest
    from pathlib import Path
    import tempfile
    expected = build(cfg, phase)
    source = Path(out(cfg, f'context-packs/phase-{phase}'))
    actual = {p.name: p.read_text() for p in source.glob('*.md')}
    if actual != expected:
        raise ValueError(f'missing or stale briefs; run srashta packs {phase}')
    class a: pass
    a.phase, a.repo, a.format = phase, repo, fmt
    tickets = read_json(out(cfg, f'tickets/phase-{a.phase}.json'))
    phase = cfg['phases'].get(int(a.phase)) or cfg['phases'].get(str(a.phase)) or {}
    destination = Path(out(cfg, f'handoff/phase-{a.phase}'))
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = tempfile.TemporaryDirectory(dir=destination.parent)
    d = staging.name

    manifest = {
        'schema_version': 2,
        'project': cfg['project'],
        'phase': int(a.phase),
        'phase_name': phase.get('name'),
        'exit_gate': phase.get('gate'),
        'repo': a.repo,
        'ticket_count': len(tickets),
        'waves': sorted({t['wave'] for t in tickets}),
        'constitution': 'constitution.md',
        'design_contract': f'contracts/phase-{a.phase}.md',
        'config': cfg.get('defaults', 'config/defaults.yaml'),
        'context_packs': 'packs/<TICKET_ID>.md',
        'blocked': {t['id']: t['blocked_on'] for t in tickets if t['blocked_on']},
        'conventions': {
            'branch': '<TICKET_ID>-<slug>',
            'tests_first': True,
            'auto_merge_on_green': 'feature tickets only, and only if no file outside owned_files changed',
            'human_review_required': ['contract', 'integration'],
            'on_contract_change_needed': 'stop and file a contract-change ticket; never edit a frozen contract',
            'network_in_tests': 'forbidden - every external dependency has an in-memory fake',
            'agent_receives': 'its context pack only, never the specification',
        },
        'routing_hint': {
            'contract': 'strongest model - an error here propagates to every ticket in the phase',
            'integration': 'strongest model - this is the phase gate',
            'feature': 'fan out across available agents',
        },
        'telemetry_required': ['attempts', 'first_run_test_failures', 'contract_change_filed',
                               'out_of_scope_files_touched', 'review_rounds', 'agent', 'diff_lines'],
        'eligibility': f'srashta eligible {a.phase} --state <state.json> --json',
        'pack_sha256': {name: digest(source / name) for name in sorted(expected)},
        'isolation': 'The orchestrator must provide each worker only its brief and permitted application context; a Git worktree is not a sandbox.',
    }
    write_json(os.path.join(d, 'manifest.json'), manifest)
    write_json(os.path.join(d, 'tickets.json'), tickets)

    src = out(cfg, f'context-packs/phase-{a.phase}')
    if os.path.isdir(src):
        dst = os.path.join(d, 'packs')
        shutil.rmtree(dst, ignore_errors=True); shutil.copytree(src, dst)

    if a.format == 'markdown-kanban':
        kd = os.path.join(d, 'kanban'); os.makedirs(kd, exist_ok=True)
        for t in tickets:
            fm = [f"---", f"id: {t['id']}", f"title: {t['title']}", f"kind: {t['kind']}",
                  f"wave: {t['wave']}", f"module: {t['module']}",
                  f"depends_on: {t['depends_on']}", f"blocked_on: {t['blocked_on']}",
                  f"status: {'blocked' if t['blocked_on'] else 'todo'}", "---", "",
                  f"Brief: packs/{t['id']}.md", "",
                  "Done when every acceptance test in the brief passes.", ""]
            open(os.path.join(kd, f"{t['id']}.md"), 'w').write('\n'.join(fm))

    if destination.exists(): shutil.rmtree(destination)
    shutil.copytree(d, destination)
    staging.cleanup()
    print(f'  handoff -> {destination}')
    print(f"    manifest.json   what this run is, and the rules of engagement")
    print(f"    tickets.json    {len(tickets)} tickets, {len(manifest['waves'])} waves")
    print(f"    packs/          one brief per ticket")
    if manifest['blocked']:
        print(f"    {len(manifest['blocked'])} ticket(s) marked blocked - the orchestrator must not claim them")
    return 0


