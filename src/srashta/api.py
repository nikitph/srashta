"""Canonical OpenAPI generation and a freeze checked against a trusted Git base."""
import difflib
import json
import subprocess
import tempfile
from pathlib import Path
import yaml
from .common import write_json, read_json
from .approvals import digest
from .execution import git, resolve

MARKER = 'docs/.openapi-frozen'


def canonical(raw):
    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict) or not str(doc.get('openapi', '')).startswith('3.'):
        raise ValueError('generator did not produce an OpenAPI 3 document')
    if not doc.get('info') or not isinstance(doc.get('paths'), dict) or not doc['paths']:
        raise ValueError('OpenAPI must contain info and at least one API path')
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def generate(cfg):
    commands = cfg.get('api_generate', ['php', 'artisan', 'scramble:export', '--path={output}', '--fail-on-unknown'])
    if not isinstance(commands, list) or not commands or not all(isinstance(x, str) for x in commands):
        raise ValueError('api_generate must be an argument array containing {output}')
    if not any('{output}' in x for x in commands): raise ValueError('api_generate requires {output}')
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp, 'openapi.json')
        command = [arg.replace('{output}', str(output)) for arg in commands]
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout, end='')
        if result.returncode: raise ValueError(f'API generator failed ({result.returncode})')
        if 'WARN [MD001]' in result.stdout:
            raise ValueError('API generation needs a migrated disposable database; model schema is unavailable')
        return canonical(output.read_text())


def git_file(ref, path):
    listing = git('ls-tree', '--name-only', ref, '--', path).decode().splitlines()
    return git('show', f'{ref}:{path}').decode() if path in listing else None


def run(cfg, action, base=None, actor=None):
    output = Path(cfg.get('api_contract', 'docs/openapi.yaml'))
    if output.is_absolute() or '..' in output.parts: raise ValueError('api_contract must be a repository-relative path')
    candidate = generate(cfg)
    marker = Path(MARKER)
    baseline = None
    frozen = None
    if base:
        base = resolve(base)  # An invalid ref must fail, never silently use another branch.
        base_cfg_text = git_file(base, 'project.yaml')
        base_cfg = yaml.safe_load(base_cfg_text) if base_cfg_text else cfg
        oldpath = base_cfg.get('api_contract', 'docs/openapi.yaml')
        baseline = git_file(base, oldpath)
        frozen_text = git_file(base, MARKER)
        frozen = json.loads(frozen_text) if frozen_text else None
        if frozen and (str(output) != oldpath or not marker.exists() or marker.read_text() != frozen_text):
            raise ValueError('candidate changed or removed the baseline freeze; use a reviewed contract-change process')
    else:
        if output.exists(): baseline = output.read_text()
        if marker.exists(): frozen = read_json(marker)
    if frozen:
        import hashlib
        actual = hashlib.sha256(candidate.encode()).hexdigest()
        if actual != frozen.get('openapi_sha256'):
            raise ValueError('generated API differs from the frozen contract; contract-change review required')
        if baseline is None or canonical(baseline) != candidate:
            raise ValueError('frozen API baseline is missing or does not match its receipt')
    if baseline and canonical(baseline) != candidate:
        print(''.join(difflib.unified_diff(canonical(baseline).splitlines(True), candidate.splitlines(True),
                                         fromfile='base API', tofile='generated API')))
    if action == 'check':
        if not base: raise ValueError('api check requires --base (the trusted PR base commit)')
        print('  API checked against base; ' + ('frozen and unchanged' if frozen else 'not frozen yet'))
        return 0
    if action == 'freeze':
        from .phase import closed
        phases = [p for p, spec in cfg.get('phases', {}).items() if spec.get('layer', 'api') == 'api']
        if not phases or any(not closed(cfg, p) for p in phases):
            raise ValueError('close every API phase before freezing the API')
        from .execution import run_checks
        run_checks(cfg)
    output.parent.mkdir(parents=True, exist_ok=True)
    # JSON is also valid YAML; serialize actual YAML when its extension says YAML.
    content = yaml.safe_dump(json.loads(candidate), sort_keys=True) if output.suffix in ('.yaml', '.yml') else candidate
    output.write_text(content)
    if action == 'freeze':
        import hashlib
        write_json(MARKER, {'schema_version': 1, 'approved_by': actor,
            'openapi_sha256': hashlib.sha256(candidate.encode()).hexdigest(), 'head': resolve('HEAD')})
    print(f'  API {action}: {output}')
    return 0
