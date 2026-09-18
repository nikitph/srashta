"""Local evidence checks. Remote merge authority remains with the orchestrator/CI."""
import hashlib
import json
import subprocess
from pathlib import Path
from .common import out, read_json, write_json
from .paths import matches


def git(*args):
    return subprocess.run(['git', *args], check=True, capture_output=True).stdout


def resolve(ref):
    return git('rev-parse', '--verify', ref + '^{commit}').decode().strip()


def run_checks(cfg):
    commands = cfg.get('verification_commands')
    if not commands or not all(isinstance(c, list) and c and all(isinstance(x, str) for x in c) for c in commands):
        raise ValueError('configure verification_commands as a nonempty list of argument arrays')
    results = []
    for command in commands:
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout, end='')
        results.append({'command': command, 'exit_code': result.returncode, 'output': result.stdout})
        if result.returncode: raise ValueError(f'verification failed: {command}')
    return results


def evidence_path(cfg, phase, ticket):
    if not __import__('re').fullmatch(r'[CTI]-[0-9]{2,3}[a-z]?', ticket):
        raise ValueError('invalid ticket ID')
    return str(Path(cfg.get('evidence_dir', 'evidence')) / f'phase-{int(phase)}' / f'{ticket}.json')


def inspect_diff(cfg, phase, ticket, base, head='HEAD'):
    base, head = resolve(base), resolve(head)
    git('merge-base', '--is-ancestor', base, head)
    if base == head: raise ValueError('verification requires at least one commit')
    # The base contains the approved plan; candidate edits cannot enlarge ownership.
    graphpath = out(cfg, f'tickets/phase-{int(phase)}.json')
    if Path(graphpath).is_absolute(): raise ValueError('Git verification requires a relative out_dir')
    records = json.loads(git('show', f'{base}:{graphpath}'))
    by_id = {t['id']: t for t in records}
    if ticket not in by_id: raise ValueError('ticket is not in the base plan')
    t = by_id[ticket]
    changed = [x.decode() for x in git('diff', '--no-renames', '--name-only', '-z', base, head).split(b'\0') if x]
    if not changed: raise ValueError('ticket has no changes')
    protected = ['project.yaml', 'tickets/**', 'spec/**', 'contracts/**', 'build/**', '.github/**',
                 'ci/**', 'hooks/**', '.srashta/**', '.claude/**', '.agents/**', 'AGENTS.md', 'CLAUDE.md', 'PROCEDURE.md',
                 'constitution.md', 'config/srashta.php', 'app/Support/ProvisionalConfig.php', 'evidence/**', 'events/**', 'retrospectives/**', cfg.get('api_contract', 'docs/openapi.yaml'), 'docs/.openapi-frozen']
    if t['kind'] != 'contract':
        # Every earlier phase contract stays frozen too.
        for path in git('ls-tree', '-r', '--name-only', base, cfg.get('out_dir', 'build') + '/tickets').decode().splitlines():
            if path.endswith('.json'):
                for contract in json.loads(git('show', f'{base}:{path}')):
                    if contract.get('kind') == 'contract': protected.extend(contract['owned_files'])
    bad = [p for p in changed if not any(matches(pattern, p) for pattern in t['owned_files'])
           or any(matches(pattern, p) for pattern in protected)]
    if bad: raise ValueError(f'{ticket} changed unowned or frozen files: {bad}')
    subjects = git('log', '--format=%s', f'{base}..{head}').decode().splitlines()
    import re
    if any(not re.search(r'(?<![A-Za-z0-9-])' + re.escape(ticket) + r'(?![A-Za-z0-9-])', s) for s in subjects):
        raise ValueError(f'every commit in the ticket range must name {ticket}')
    return {'schema_version': 1, 'phase': int(phase), 'ticket': ticket, 'base': base, 'head': head, 'files': changed}


def assert_clean(cfg):
    changed = set(git('diff', '--name-only', 'HEAD').decode().splitlines())
    changed.update(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
    allowed = [cfg.get('events_dir', 'events') + '/**', cfg.get('evidence_dir', 'evidence') + '/**',
               cfg.get('retrospectives_dir', 'retrospectives') + '/**']
    dirty = [p for p in changed if not any(matches(pattern,p) for pattern in allowed)]
    if dirty: raise ValueError(f'verification requires committed application and planning inputs: {sorted(dirty)}')


def verify(cfg, phase, ticket, base):
    record = inspect_diff(cfg, phase, ticket, base)
    assert_clean(cfg)
    # Commands are project configuration, executed intentionally by this command.
    baseline = __import__('yaml').safe_load(git('show', f"{record['base']}:project.yaml"))
    record['checks'] = run_checks(baseline)
    assert_clean(cfg)
    if resolve('HEAD') != record['head']:
        raise ValueError('verification changed tracked files or HEAD; commit and verify again')
    write_json(evidence_path(cfg, phase, ticket), record)
    print(f'  verified {ticket} at {record["head"]}')
    return 0


def merge_evidence(cfg, phase, ticket, data):
    evidence = read_json(evidence_path(cfg, phase, ticket))
    if evidence['phase'] != int(phase) or evidence['ticket'] != ticket:
        raise ValueError('evidence is for a different ticket or phase')
    if data.get('head') != evidence['head']:
        raise ValueError('merged event head must equal the verified commit')
    git('merge-base', '--is-ancestor', evidence['head'], 'HEAD')
    inspect_diff(cfg, phase, ticket, evidence['base'], evidence['head'])
    if not evidence.get('checks') or any(c['exit_code'] for c in evidence['checks']):
        raise ValueError('merge lacks passing verification')
    return hashlib.sha256(Path(evidence_path(cfg, phase, ticket)).read_bytes()).hexdigest()
