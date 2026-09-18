"""Resolve a ticket phase from the trusted base graph."""
import json, subprocess, sys
base, ticket = sys.argv[1:]
paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', base, 'build/tickets'], text=True).splitlines()
phases = []
for path in paths:
    if path.endswith('.json'):
        graph = json.loads(subprocess.check_output(['git', 'show', f'{base}:{path}']))
        if any(t['id'] == ticket for t in graph):
            phases.append(path.rsplit('phase-', 1)[-1].removesuffix('.json'))
if len(phases) != 1: raise SystemExit(f'ticket {ticket}: expected one phase, found {phases}')
print(phases[0])
