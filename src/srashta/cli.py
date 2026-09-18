#!/usr/bin/env python3
"""srashta — स्रष्टा, the one who brings into existence.

Bookkeeping and enforcement for turning a spec into agent-ready tickets.

This CLI NEVER CALLS A MODEL. It parses, assigns, derives, generates, validates and
traces. Every act of judgment happens in your agent harness, on your subscription.
The division is exact:

    srashta decides what is CONSISTENT.
    your agent decides what is GOOD.
"""
import argparse, os, sys
from importlib import import_module
from . import __version__

def _cfg(path='project.yaml', required=True, enforce_pin=True):
    from .common import load_project
    if not os.path.exists(path):
        if required:
            raise SystemExit("  no project.yaml here. run `srashta init <name>` first,"
                             " or cd into a project.")
        return {}
    cfg = load_project(path)
    pin = cfg.get('srashta_version')
    # `upgrade` is the remedy the guard names, so the guard must not block it. It did:
    # a pinned project could never be migrated, and the message told the operator to run
    # the one command that could not run.
    if pin and pin != __version__ and enforce_pin:
        raise SystemExit(
            f"  this project pins srashta {pin}; you have {__version__}.\n"
            f"  the validator IS the conformance definition, so a silent version change\n"
            f"  would silently change what 'valid' means.\n"
            f"  run `srashta upgrade` to migrate deliberately, or install {pin}.")
    return cfg

def main(argv=None):
    # piping into head/less is normal CLI use; do not traceback on it
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass
    p = argparse.ArgumentParser(prog='srashta', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--version', action='version', version=f'srashta {__version__}')
    sub = p.add_subparsers(dest='cmd', metavar='<command>')

    def add(name, help):
        return sub.add_parser(name, help=help)

    a = add('init',     'create a project repo from the blueprint')
    a.add_argument('name'); a.add_argument('--dest', default=None)
    a.add_argument('--stack', default='laravel-react', choices=['laravel-react', 'none'])
    a.add_argument('--run-scaffold', action='store_true')

    add('status',   'where is this project, and whose turn is it')

    a = add('run',      'the whole chain, degrading rather than blocking')
    a.add_argument('--phase', type=int, default=None); a.add_argument('--verbose', action='store_true')

    add('extract',  'parse the spec into requirements')
    add('lint',     'requirements smells and structural completeness')
    add('dsm',      'derive modules and cross-module flows')
    add('assign',   'assign every requirement to one module and one phase')

    a = add('waves',    'derive waves from the authored ticket graph');  a.add_argument('phase')
    a = add('packs',    'write one bounded context pack per ticket'); a.add_argument('phase')
    a = add('validate', 'THE GATE - non-zero on any defect');        a.add_argument('phase')
    a = add('export',   'handoff bundle for the orchestrator');       a.add_argument('phase')
    a.add_argument('--repo', default=None)
    a.add_argument('--format', default='generic', choices=['generic', 'markdown-kanban'])

    a = add('eligible', 'which tickets may be claimed right now')
    a.add_argument('phase'); a.add_argument('--state', default='state.json')
    a.add_argument('--json', action='store_true')

    a = add('gentests', 'generate transition tests from a table')
    a.add_argument('--machines', default='machines.yaml')
    a.add_argument('--flavour', default='pest', choices=['pest', 'pytest', 'vitest'])
    a.add_argument('--out', default='tests/Generated')

    a = add('event',    'record one execution event (append-only)')
    a.add_argument('ticket', nargs='?'); a.add_argument('kind', nargs='?')
    a.add_argument('--phase', default='0'); a.add_argument('--data', default=None)
    a.add_argument('--agent', default=None)
    a.add_argument('--summary', action='store_true'); a.add_argument('--list-kinds', action='store_true')

    a = add('trace',    'why does this exist / what breaks if it changes')
    a.add_argument('target', help='a requirement id, a ticket id, or text containing one')

    a = add('skills',   'compare or sync this project\'s skills against the blueprint')
    a.add_argument('--diff', action='store_true', help='show what differs (default)')
    a.add_argument('--full', action='store_true', help='line-by-line rather than a summary')
    a.add_argument('--sync', action='store_true', help='take the blueprint version')
    a.add_argument('--promote', nargs='*', metavar='SKILL',
                   help='open a PR sending your version up to the blueprint repo')
    a.add_argument('--force', action='store_true', help='sync despite discarding local edits')

    add('upgrade',  'migrate this project to the installed srashta version')

    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help(); return 0

    if args.cmd == 'init':
        m = import_module('.init', package='srashta')
        return m.run(args.name, args.dest or f'./{args.name}', args.stack, args.run_scaffold)

    if args.cmd == 'status':
        return import_module('.status', package='srashta').main_cli()

    cfg = _cfg(enforce_pin=args.cmd not in ('upgrade', 'status'))
    if args.cmd == 'run':
        return import_module('.run', package='srashta').run(cfg, args.phase, args.verbose)
    if args.cmd in ('extract', 'lint', 'dsm', 'assign'):
        r = import_module(f'.{args.cmd}', package='srashta').main(cfg)
        return r if isinstance(r, int) else 0
    if args.cmd == 'waves':
        return import_module('.waves', package='srashta').main(cfg, args.phase)
    if args.cmd == 'packs':
        return import_module('.packs', package='srashta').main(cfg, args.phase) or 0
    if args.cmd == 'validate':
        return import_module('.validate', package='srashta').main(cfg, args.phase)
    if args.cmd == 'export':
        return import_module('.export', package='srashta').run(cfg, args.phase, args.repo, args.format)
    if args.cmd == 'eligible':
        return import_module('.eligible', package='srashta').run(cfg, args.phase, args.state, args.json)
    if args.cmd == 'gentests':
        import yaml
        m = import_module('.gentests', package='srashta')
        w, c = m.generate(yaml.safe_load(open(args.machines)), args.flavour, args.out)
        tp = sum(v[0] for v in c.values()); tf = sum(v[1] for v in c.values())
        for n, (x, y) in c.items(): print(f"  {n:24s} {x:3d} permitted {y:4d} sneak-path")
        print(f"  generated {len(w)} file(s), {tp+tf} tests ({tp} permitted, {tf} forbidden)")
        return 0
    if args.cmd == 'event':
        return import_module('.events', package='srashta').main(cfg, args)
    if args.cmd == 'skills':
        return import_module('.skills', package='srashta').main(args, cfg)
    if args.cmd == 'trace':
        return import_module('.trace', package='srashta').main(cfg, args.target)
    if args.cmd == 'upgrade':
        import yaml
        c = yaml.safe_load(open('project.yaml')); old = c.get('srashta_version')
        c['srashta_version'] = __version__
        yaml.safe_dump(c, open('project.yaml', 'w'), sort_keys=False, width=100)
        print(f"  pinned {old} -> {__version__}")
        print(f"  now re-run `srashta validate <phase>` for every decomposed phase:")
        print(f"  a changed validator can turn a previously valid graph invalid, and you")
        print(f"  want to see that now rather than mid-execution.")
        return 0
    return 0
