"""Create a repo without overwriting existing work; scaffold before adding metadata."""
import os
import re
import shutil
import subprocess
import tempfile
from importlib.resources import files
from pathlib import Path
import yaml
from . import __version__

SCAFFOLD = {'laravel-react': [
    ['composer', 'create-project', 'laravel/react-starter-kit', '.', '--no-interaction', '--prefer-dist'],
    ['php', 'artisan', 'install:api', '--no-interaction'],
    ['composer', 'require', 'dedoc/scramble', '--no-interaction'],
    ['composer', 'config', 'allow-plugins.pestphp/pest-plugin', 'true'],
    ['composer', 'require', '--dev', 'pestphp/pest:^3', 'pestphp/pest-plugin-laravel:^3', '--with-all-dependencies', '--no-interaction'],
], 'none': []}


def bootstrap(root='.'):
    root = Path(root).resolve()
    subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=root, check=True, capture_output=True)
    for hook in (root / 'hooks').glob('*'):
        hook.chmod(0o755)
    subprocess.run(['git', 'config', '--local', 'core.hooksPath', 'hooks'], cwd=root, check=True)
    print('  repository hooks enabled (run srashta bootstrap after each clone)')
    return 0


def scaffold(stack, root):
    if stack not in SCAFFOLD: raise ValueError(f'unknown stack {stack}')
    for command in SCAFFOLD[stack]:
        print('  $ ' + ' '.join(command), flush=True)
        subprocess.run(command, cwd=root, check=True)


def run(name, dest, stack='laravel-react', run_scaffold=False):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name):
        raise ValueError('name must contain only letters, digits, dots, underscores and hyphens')
    target = Path(dest).resolve()
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError(f'{target} is not empty; init never overwrites an existing project')
    target.parent.mkdir(parents=True, exist_ok=True)
    # All fallible scaffolding happens in an empty staging directory.
    with tempfile.TemporaryDirectory(prefix='.srashta-init-', dir=target.parent) as temporary:
        root = Path(temporary)
        if run_scaffold: scaffold(stack, root)
        template = files('srashta') / 'templates'
        for directory in ('spec', 'contracts', 'config', 'retrospectives', 'events', 'evidence', 'tickets', 'build'):
            (root / directory).mkdir(exist_ok=True)
        for directory in ('docs', 'schemas', 'ci', 'hooks'):
            shutil.copytree(str(template / directory), root / directory, dirs_exist_ok=True)
        for source, destination in [('constitution.md', 'constitution.md'), ('PROCEDURE.md', 'PROCEDURE.md'),
            ('spec-skeleton.md', 'spec/_skeleton.md'), ('machines.yaml', 'machines.yaml'),
            ('adapters/CLAUDE.md', 'CLAUDE.md'), ('adapters/AGENTS.md', 'AGENTS.md')]:
            shutil.copy(str(template / source), root / destination)
        # Canonical editable guides plus native entrypoints referencing those guides.
        skillroot = root / '.claude/skills'
        shutil.copytree(str(template / 'skills'), skillroot)
        from .skills import entrypoints
        entrypoints(root)
        cfg = yaml.safe_load((template / 'project.yaml').read_text().replace('<name>', name))
        cfg.update(srashta_version=__version__, artifact_version=2, tickets_dir='tickets', stack=stack)
        (root / 'project.yaml').write_text(yaml.safe_dump(cfg, sort_keys=False))
        (root / 'config/defaults.yaml').write_text('{}\n')
        if stack == 'laravel-react':
            support = root / 'app/Support'
            support.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(template / 'laravel/ProvisionalConfig.php'), support / 'ProvisionalConfig.php')
            (root / 'config/srashta.php').write_text("<?php\nreturn ['values' => [], 'blocked_keys' => []];\n")
        (root / 'PROJECT.md').write_text(f'# {name}\n\nRun `srashta status`. Follow PROCEDURE.md.\n\n'
            'Author ticket graphs in tickets/phase-N.json. build/ is regenerated.\n'
            'After cloning, run `srashta bootstrap` to enable repository hooks.\n')
        with (root / '.gitignore').open('a') as stream:
            stream.write('\nvendor/\nnode_modules/\n.env\n__pycache__/\nbuild/run.log\n')
        runtime = root / '.srashta/runtime/srashta'
        runtime.mkdir(parents=True)
        for module in files('srashta').iterdir():
            if module.name.endswith('.py'): shutil.copy(str(module), runtime / module.name)
        workflows = root / '.github/workflows'
        workflows.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(template / 'ci/api-contract.yml'), workflows / 'srashta.yml')
        for script in (root / 'ci').glob('*.sh'): script.chmod(0o755)
        if stack != 'none' and not run_scaffold:
            (root / 'SETUP.md').write_text('The application has not been scaffolded. For a working Laravel '
                'starter create a fresh destination with `srashta init NAME --run-scaffold`. '
                'This planning-only repository is usable with an application you integrate separately.\n')
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        bootstrap(root)
        # Leave the initial commit to the operator; init does not depend on Git identity.
        if target.exists(): target.rmdir()
        shutil.move(str(root), target)
    print(f'  created {target}; review and commit the initial files')
    return 0
