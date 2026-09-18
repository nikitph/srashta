"""Content-bound human approval receipts. Git/CI controls who may modify them."""
import hashlib
import json
from pathlib import Path
from .common import write_json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def locations(cfg, phase, root='.'):
    base = Path(root) / cfg.get('contracts_dir', 'contracts')
    return base / f'phase-{int(phase)}.md', base / f'phase-{int(phase)}.approved'


def approve(cfg, phase, actor):
    design, receipt = locations(cfg, phase)
    if not design.is_file() or not design.read_text().strip():
        raise SystemExit(f'ERROR: write {design} before approval')
    if not actor.strip():
        raise SystemExit('ERROR: approval requires the reviewing operator name')
    write_json(str(receipt), {'schema_version': 1, 'phase': int(phase),
                            'approved_by': actor, 'design_sha256': digest(design)})
    print(f'  approved {design}; commit {receipt} with it')
    return 0


def problem(cfg, phase, root='.'):
    design, receipt = locations(cfg, phase, root)
    if not design.is_file():
        return f'{design} does not exist — write the contract design first'
    if not receipt.is_file():
        return f'{receipt} does not exist — an operator must run srashta approve {phase} --by NAME'
    try:
        data = json.loads(receipt.read_text())
        if (not isinstance(data, dict) or data.get('schema_version') != 1
                or data.get('phase') != int(phase) or not data.get('approved_by')):
            return f'{receipt} is not a valid approval receipt'
        if data.get('design_sha256') != digest(design):
            return f'{design} changed after approval; operator review and approval are required again'
    except (ValueError, OSError):
        return f'{receipt} is not a content-bound approval; operator must approve again'
    return None
