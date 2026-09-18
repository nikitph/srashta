"""Authored tickets are source. Normalised executable tickets are disposable views."""
import copy
from pathlib import Path
from .common import read_json, write_json, out


def source_path(cfg, phase):
    return Path(cfg.get('tickets_dir', 'tickets')) / f'phase-{int(phase)}.json'


def derive(cfg, phase):
    from .waves import finalise
    source = source_path(cfg, phase)
    if not source.is_file():
        raise SystemExit(f'ERROR: author {source} first; legacy build/tickets requires srashta upgrade')
    records = copy.deepcopy(read_json(str(source)))
    questions = cfg.get('open_questions', {})
    for ticket in records:
        ticket['blocked_on'] = [q for q in ticket.get('blocked_on', [])
                                if not questions.get(q, {}).get('answered')]
    return finalise(records, shared=cfg.get('shared_resources'))


def migrate(cfg):
    """Preserve old planning data; never discard authored edges or infer approval."""
    for old in sorted(Path(cfg.get('out_dir', 'build')).glob('tickets/phase-*.json')):
        phase = int(old.stem.removeprefix('phase-'))
        target = source_path(cfg, phase)
        if target.exists():
            continue
        records = read_json(str(old))
        for t in records:
            for field in ('wave', 'derived_by', 'contracts_used', 'telemetry'):
                t.pop(field, None)
        write_json(str(target), records)
        print(f'  preserved {old} as authored source {target}; review inherited blockers and serial edges')


def write(cfg, phase):
    records, drift, edges = derive(cfg, phase)
    write_json(out(cfg, f'tickets/phase-{phase}.json'), records)
    return records, drift, edges
