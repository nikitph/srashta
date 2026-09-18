#!/usr/bin/env python3
"""srashta init — create a project repo from the blueprint.

Resolves the bootstrap question: contracts are built by wave-0 tickets, which need an
orchestrator, which needs a repo with a working stack. So the repo is created here,
before any ticket exists. Nothing circular.

It also drops the harness adapters in, so that whichever tool you open in this folder
- Claude Code, Codex, Cursor - already knows the procedure.
"""
import os, shutil, subprocess, textwrap
from importlib.resources import files
from . import __version__

SCAFFOLD = {
 'laravel-react': [
   'composer create-project laravel/laravel .',
   'php artisan install:api',
   'composer require laravel/breeze --dev && php artisan breeze:install react --typescript',
   'npm install && npm install -D culori yaml @playwright/test',
   'composer require dedoc/scramble',      # annotation-free OpenAPI from routes
 ],
 'none': [],
}

def run(name, dest, stack='laravel-react', run_scaffold=False):
    T = files('srashta') / 'templates'
    d = os.path.abspath(dest)
    os.makedirs(d, exist_ok=True)
    cp = lambda rel, to: shutil.copy(str(T / rel), os.path.join(d, to))

    for sub in ('spec', 'contracts', 'config', 'retrospectives', 'events', 'build',
                '.claude/skills'):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    shutil.copytree(str(T / 'docs'), os.path.join(d, 'docs'), dirs_exist_ok=True)
    shutil.copytree(str(T / 'schemas'), os.path.join(d, 'schemas'), dirs_exist_ok=True)
    shutil.copytree(str(T / 'skills'), os.path.join(d, '.claude/skills'), dirs_exist_ok=True)

    cp('constitution.md', 'constitution.md')
    cp('PROCEDURE.md', 'PROCEDURE.md')
    cp('spec-skeleton.md', 'spec/_skeleton.md')
    cp('brand.yaml', 'brand.yaml.template')
    cp('machines.yaml', 'machines.yaml')
    shutil.copytree(str(T / 'ci'), os.path.join(d, 'ci'), dirs_exist_ok=True)
    shutil.copytree(str(T / 'hooks'), os.path.join(d, 'hooks'), dirs_exist_ok=True)
    # harness adapters: the mechanism that makes "open any tool here" true
    cp('adapters/CLAUDE.md', 'CLAUDE.md')
    cp('adapters/AGENTS.md', 'AGENTS.md')

    pj = (T / 'project.yaml').read_text().replace('<name>', name)
    open(os.path.join(d, 'project.yaml'), 'w').write(pj)

    open(os.path.join(d, 'PROJECT.md'), 'w').write(textwrap.dedent(f"""\
        # {name}

        This repo is the project. Spec, brand, contracts, tickets, briefs and execution
        history all live here, so any session — a planning agent, an orchestrator, or you —
        picks up from the state on disk rather than from a conversation.

        ```bash
        srashta status
        ```

        tells you what is done, what is next, and whose turn it is.

        | Path | What |
        |---|---|
        | `spec/` | the PRD |
        | `brand.yaml` | brand identity |
        | `project.yaml` | modules, phases, overrides, open questions |
        | `config/defaults.yaml` | every parameter, with defaults |
        | `contracts/phase-N.md` | contract design; `.approved` is the human gate |
        | `build/` | **derived** — regenerated from the above, never hand-edited |
        | `build/handoff/phase-N/` | what the orchestrator consumes |
        | `events/phase-N.jsonl` | append-only execution history |
        | `retrospectives/` | what each phase taught |

        `PROCEDURE.md` is the method; `docs/lifecycle.md` is who does what.
        """))

    open(os.path.join(d, '.gitignore'), 'w').write(
        "vendor/\nnode_modules/\n.env\n__pycache__/\nbuild/run.log\n")

    # the API contract is a build output; nothing in the repo hand-edits it
    open(os.path.join(d, '.gitattributes'), 'w').write(
        "docs/openapi.yaml linguist-generated=true merge=ours\n")

    steps = SCAFFOLD.get(stack, [])
    if steps and run_scaffold:
        for c in steps:
            print(f"  $ {c}")
            subprocess.run(c, shell=True, cwd=d, check=False)
    elif steps:
        open(os.path.join(d, 'SETUP.md'), 'w').write(
            f"# Stack scaffold ({stack})\n\nRun in the repo root, then delete this file:\n\n"
            "```bash\n" + '\n'.join(steps) + "\n```\n")

    if not os.path.exists(os.path.join(d, '.git')):
        subprocess.run('git init -q', shell=True, cwd=d, check=False)

    # A hook that must be installed by hand is a hook that is not installed.
    # This must follow `git init`: pre-creating .git/hooks makes git init a no-op.
    hd = os.path.join(d, '.git', 'hooks')
    if os.path.isdir(os.path.join(d, '.git')):
        os.makedirs(hd, exist_ok=True)
        for h in os.listdir(os.path.join(d, 'hooks')):
            shutil.copy(os.path.join(d, 'hooks', h), os.path.join(hd, h))
            os.chmod(os.path.join(hd, h), 0o755)

    subprocess.run('git add -A '
                   f'&& git commit -q -m "Initialise {name} (srashta {__version__})"',
                   shell=True, cwd=d, check=False)

    print(f"\n  {name} created at {d}")
    print(f"  srashta {__version__} pinned in project.yaml")
    if steps and not run_scaffold:
        print(f"  stack scaffold commands written to SETUP.md")
    print(f"\n  cd {dest} && srashta status\n")
    return 0
