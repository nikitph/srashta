"""Close a phase with checks, phase-scoped merge evidence, and a retrospective."""
from pathlib import Path
from . import events
from .common import out, read_json, write_json
from .execution import run_checks, merge_evidence, resolve, assert_clean
from .approvals import digest


def receipt_path(cfg, phase):
    return Path(cfg.get('phase_receipts_dir', 'retrospectives')) / f'phase-{int(phase)}.closed.json'


def fingerprint(cfg, phase):
    from .tickets import source_path
    paths = [Path('project.yaml'), Path(cfg['spec']['path']), source_path(cfg, phase),
             Path(out(cfg, f'tickets/phase-{phase}.json')),
             Path(cfg.get('contracts_dir', 'contracts')) / f'phase-{phase}.md',
             Path(cfg.get('contracts_dir', 'contracts')) / f'phase-{phase}.approved',
             Path(cfg.get('retrospectives_dir', 'retrospectives')) / f'phase-{phase}.md',
             Path(events.path(cfg, phase))]
    return {str(p): digest(p) for p in paths}


def closed(cfg, phase):
    try:
        receipt = read_json(receipt_path(cfg, phase))
        return receipt['inputs'] == fingerprint(cfg, phase)
    except (OSError, ValueError, KeyError): return False


def close(cfg, phase, actor):
    from .validate import check
    *_, errors, _ = check(cfg, phase)
    if errors: raise ValueError('\n'.join(errors))
    tickets = read_json(out(cfg, f'tickets/phase-{phase}.json'))
    log = events.read(cfg, phase)
    summary = events.derive(log)
    for t in tickets:
        info = summary.get(t['id'], {})
        if not info.get('merged') or info.get('brief_sufficient') is None:
            raise ValueError(f'{t["id"]} needs a verified merge and brief_feedback')
        merged = [e for e in log if e['ticket'] == t['id'] and e['kind'] == 'merged'][-1]
        if merge_evidence(cfg, phase, t['id'], merged.get('data', {})) != merged['data'].get('evidence_sha256'):
            raise ValueError(f'{t["id"]} evidence changed since merge')
    retro = Path(cfg.get('retrospectives_dir', 'retrospectives')) / f'phase-{phase}.md'
    if not retro.exists() or not retro.read_text().strip(): raise ValueError(f'write {retro} first')
    assert_clean(cfg)
    checks = run_checks(cfg)
    assert_clean(cfg)
    write_json(str(receipt_path(cfg, phase)), {'schema_version': 1, 'phase': int(phase), 'closed_by': actor,
        'head': resolve('HEAD'), 'inputs': fingerprint(cfg, phase), 'checks': checks})
    print(f'  phase {phase} closed; commit the receipt and evidence')
    return 0
