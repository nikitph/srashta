"""Shared resources: contention that file ownership cannot see.

Three tickets with disjoint owned_files still all need routes/api.php. The fix is
mostly to remove the contention rather than manage it — and where it cannot be
removed, to make the serialisation an EDGE IN THE GRAPH rather than a runtime stall.
A stall is invisible; an edge is reviewable, and the graph stays a DAG.
"""
import json, os, pytest
from srashta import extract, assign, validate, packs
from srashta.waves import finalise

ALL = ['FR-ACC-001','FR-ACC-002','FR-ACC-003','FR-ACC-004',
       'FR-NOT-001','FR-NOT-002','NFR-001','NFR-002']

SHARED = {
  'api_routes': {'paths': ['routes/api.php'], 'strategy': 'fragment',
                 'fragment': 'routes/api/{module}.php'},
  'deps':       {'paths': ['composer.json', 'composer.lock'], 'strategy': 'contract_only'},
  'container':  {'paths': ['bootstrap/app.php'], 'strategy': 'serialise'},
}

def t(id, reqs=(), deps=(), files=None, touches=(), module='identity', **kw):
    d = dict(id=id, title=id, module=module, depends_on=list(deps),
             owned_files=files or [f'app/{id}.php'], requirements=list(reqs), asserts=[],
             acceptance_tests=['x'], evidence=['y'], blocked_on=[], wave_hint=None,
             layer='api', serves=['J1.1','J1.2'], touches=list(touches))
    d.update(kw); return d

def prep(cfg):
    extract.main(cfg); assign.main(cfg)
    os.makedirs('contracts', exist_ok=True)
    open('contracts/phase-0.md','w').write('c'); __import__('srashta.approvals', fromlist=['approve']).approve(cfg, 0, 'test reviewer')
    cfg['shared_resources'] = SHARED

def write(cfg, ts):
    fin, _, added = finalise(ts, shared=cfg.get('shared_resources'))
    os.makedirs('build/tickets', exist_ok=True)
    json.dump(fin, open('build/tickets/phase-0.json','w'), indent=1)
    return fin, added

# ---- owning a shared path without declaring it ---------------------------

def test_owning_a_shared_path_without_declaring_it_is_a_defect(cfg, capsys):
    prep(cfg)
    write(cfg, [t('C-01', ALL), t('T-01', ALL, ['C-01'], ['routes/api.php'])])
    assert validate.main(cfg, 0, quiet=True) == 1
    out = capsys.readouterr().out
    assert 'shared resource' in out and 'api_routes' in out

# ---- fragment: remove the contention ------------------------------------

def test_a_fragmented_resource_needs_no_edge_at_all(cfg, capsys):
    """Three endpoint tickets, three route fragments, one wave. Nothing serialises."""
    prep(cfg)
    fin, added = write(cfg, [
        t('C-01', ALL),
        t('T-01', ALL, ['C-01'], ['app/a.php', 'routes/api/identity.php'],
          touches=['api_routes']),
        t('T-02', [], ['C-01'], ['app/b.php', 'routes/api/billing.php'],
          touches=['api_routes'], module='billing'),
        t('T-03', [], ['C-01'], ['app/c.php', 'routes/api/notifications.php'],
          touches=['api_routes'], module='notifications')])
    assert added == []
    assert len({x['wave'] for x in fin if x['id'].startswith('T-')}) == 1
    assert validate.main(cfg, 0, quiet=True) == 0

def test_owning_the_aggregate_instead_of_the_fragment_is_a_defect(cfg, capsys):
    prep(cfg)
    write(cfg, [t('C-01', ALL),
                t('T-01', ALL, ['C-01'], ['routes/api.php'], touches=['api_routes'])])
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'routes/api/identity.php' in capsys.readouterr().out   # names the fragment

# ---- contract_only: shared structure belongs to contracts ---------------

def test_a_feature_ticket_may_not_touch_a_contract_only_resource(cfg, capsys):
    prep(cfg)
    write(cfg, [t('C-01', ALL),
                t('T-01', ALL, ['C-01'], ['app/a.php', 'composer.json'],
                  touches=['deps'])])
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'contract' in capsys.readouterr().out.lower()

def test_a_contract_ticket_may(cfg, capsys):
    prep(cfg)
    write(cfg, [t('C-01', ALL, files=['app/c.php', 'composer.json'], touches=['deps']),
                t('T-01', ALL, ['C-01'])])
    assert validate.main(cfg, 0, quiet=True) == 0

# ---- serialise: the edge is explicit and the DAG survives ---------------

def test_serialised_tickets_get_an_explicit_edge_not_a_runtime_wait(cfg, capsys):
    prep(cfg)
    fin, added = write(cfg, [
        t('C-01', ALL),
        t('T-01', ALL, ['C-01'], ['app/a.php', 'bootstrap/app.php'], touches=['container']),
        t('T-02', [], ['C-01'], ['app/b.php', 'bootstrap/app.php'], touches=['container'])])
    by = {x['id']: x for x in fin}
    assert 'T-01' in by['T-02']['depends_on']          # chained, deterministic by id
    assert by['T-02']['wave'] > by['T-01']['wave']     # and it shows in the graph
    assert added and added[0][0] == 'container'
    assert validate.main(cfg, 0, quiet=True) == 0      # still a valid DAG

def test_a_long_serialisation_chain_is_warned_about(cfg, capsys):
    """Serialising many tickets is correct but is the signal to fragment instead."""
    prep(cfg)
    ts = [t('C-01', ALL)] + [
        t(f'T-{i:02d}', ALL if i == 1 else [], ['C-01'],
          [f'app/{i}.php', 'bootstrap/app.php'], touches=['container'])
        for i in range(1, 6)]
    write(cfg, ts)
    validate.main(cfg, 0, quiet=True)
    out = capsys.readouterr().out
    assert 'serialis' in out.lower() and 'fragment' in out.lower()

def test_serialisation_never_creates_a_cycle(cfg):
    """Chaining must respect existing edges, not invert them."""
    prep(cfg)
    fin, _ = write(cfg, [
        t('C-01', ALL),
        t('T-02', ALL, ['C-01'], ['app/b.php', 'bootstrap/app.php'], touches=['container']),
        t('T-01', [], ['C-01', 'T-02'], ['app/a.php', 'bootstrap/app.php'],
          touches=['container'])])
    by = {x['id']: x for x in fin}
    assert 'T-02' in by['T-01']['depends_on']
    assert 'T-01' not in by['T-02']['depends_on']      # would be a cycle
    assert by['T-01']['wave'] > by['T-02']['wave']
