"""Export one brief plus application files, without planning documents or Git history."""
import shutil
import tempfile
from pathlib import Path
from .packs import build
from .execution import git, resolve
from .paths import matches
from .common import write_json, read_json, out

CONTEXT = ['app/**', 'bootstrap/**', 'config/**', 'database/migrations/**', 'database/factories/**',
           'routes/**', 'tests/**', 'resources/**', 'public/index.php', 'artisan', 'composer.json',
           'composer.lock', 'package.json', 'package-lock.json', 'phpunit.xml', 'vite.config.*', 'tsconfig.json',
           '.env.example', 'docs/openapi.yaml', 'docs/openapi.json']
DENY = ['spec/**', 'tickets/**', 'contracts/**', 'build/**', 'events/**', 'retrospectives/**', 'evidence/**',
        '.git/**', '.claude/**', '.agents/**', '.srashta/**', 'AGENTS.md', 'CLAUDE.md', 'project.yaml',
        'PROCEDURE.md', '.env', '.env.*', '**/*.sqlite']


def run(cfg, phase, ticket, destination):
    bodies = build(cfg, phase)
    if ticket + '.md' not in bodies: raise ValueError('unknown ticket')
    target = Path(destination).resolve()
    if target.exists(): raise ValueError('worker destination must not exist')
    context = cfg.get('worker_context', CONTEXT)
    target.parent.mkdir(parents=True, exist_ok=True)
    source_commit = resolve('HEAD')
    records = read_json(out(cfg, f'tickets/phase-{phase}.json'))
    record = next(t for t in records if t['id'] == ticket)
    # Only committed regular blobs. No symlink can expose a parent or omitted file.
    entries = git('ls-tree', '-r', '-z', source_commit).split(b'\0')
    copied = []
    with tempfile.TemporaryDirectory(dir=target.parent, prefix='.worker-') as temp:
        root = Path(temp)
        for entry in entries:
            if not entry: continue
            meta, rawpath = entry.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            path = rawpath.decode()
            if not any(matches(p, path) for p in context): continue
            if path != '.env.example' and any(matches(p, path) for p in DENY): continue
            if kind != 'blob' or mode not in ('100644', '100755'):
                raise ValueError(f'worker context cannot include a symlink/submodule: {path}')
            output = root / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(git('cat-file', 'blob', oid))
            output.chmod(0o755 if mode == '100755' else 0o644)
            copied.append(path)
        (root / 'BRIEF.md').write_text(bodies[ticket + '.md'])
        write_json(str(root / 'WORKER.json'), {'schema_version': 1, 'ticket': ticket, 'phase': int(phase),
            'source_commit': source_commit, 'owned_files': record['owned_files'], 'context_files': copied,
            'instruction': 'Read BRIEF.md. Return a patch and evidence; the orchestrator records events and performs merges.'})
        shutil.move(temp, target)
    print(f'  worker input -> {target}; {len(copied)} application files, one brief, no Git history')
    print('  launch this directory inside the orchestrator sandbox; copying files does not constrain host access')
    return 0
