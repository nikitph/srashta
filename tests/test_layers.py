import json, os
from srashta import extract, assign, validate
from srashta.waves import finalise

ALL = ['FR-ACC-001','FR-ACC-002','FR-ACC-003','FR-ACC-004',
       'FR-NOT-001','FR-NOT-002','NFR-001','NFR-002']

def t(id, reqs, deps=(), files=None, layer=None, serves=(), module='identity'):
    return dict(id=id, title=id, module=module, depends_on=list(deps),
                owned_files=files or ['app/x.php'], requirements=list(reqs), asserts=[],
                acceptance_tests=['x'], evidence=['y'], blocked_on=[], wave_hint=None,
                layer=layer, serves=list(serves))

def write(ts):
    fin, _, _ = finalise(ts)
    os.makedirs('build/tickets', exist_ok=True)
    json.dump(fin, open('build/tickets/phase-0.json','w'), indent=1)

def prep(cfg):
    extract.main(cfg); assign.main(cfg)
    os.makedirs('contracts', exist_ok=True)
    open('contracts/phase-0.md','w').write('c'); __import__('srashta.approvals', fromlist=['approve']).approve(cfg, 0, 'test reviewer')

def sound():
    return [t('C-00', [], files=['resources/css/app.css'], layer='surface'),
            t('C-01', ALL, layer='api'),
            t('T-01', ALL, ['C-01'], layer='api', serves=['J1.1','J1.2']),
            t('T-02', [], ['C-00','T-01'], files=['resources/js/pages/a.tsx'],
              layer='surface')]

def test_a_layered_graph_passes(cfg, capsys):
    prep(cfg); write(sound())
    assert validate.main(cfg, 0, quiet=True) == 0

def test_a_ticket_spanning_layers_is_a_defect(cfg, capsys):
    prep(cfg)
    ts = sound(); ts[2]['owned_files'] = ['app/x.php', 'resources/js/pages/a.tsx']
    write(ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'outside that layer' in capsys.readouterr().out

def test_a_screen_with_no_endpoint_behind_it_is_a_defect(cfg, capsys):
    prep(cfg)
    ts = sound(); ts[3]['depends_on'] = ['C-00']
    write(ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'reaches no' in capsys.readouterr().out

def test_a_surface_ticket_must_rest_on_the_design_system(cfg, capsys):
    prep(cfg)
    ts = sound(); ts[3]['depends_on'] = ['T-01']
    write(ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'must rest on contract C-00' in capsys.readouterr().out

def test_an_api_ticket_needs_no_design_system(cfg, capsys):
    """The whole point: backend work does not wait on brand."""
    prep(cfg)
    ts = [t('C-01', ALL, layer='api'),
          t('T-01', ALL, ['C-01'], layer='api', serves=['J1.1','J1.2'])]
    write(ts)
    assert validate.main(cfg, 0, quiet=True) == 0

def test_coupled_must_be_declared_not_assumed(cfg, capsys):
    prep(cfg)
    ts = sound()
    ts[2]['layer'] = 'coupled'; ts[2]['module'] = 'identity'      # not in transport_coupled
    write(ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'not in transport_coupled' in capsys.readouterr().out

def test_a_declared_coupled_module_may_span_layers(cfg, capsys):
    prep(cfg)
    ts = sound()
    ts[2]['layer'] = 'coupled'; ts[2]['module'] = 'notifications'
    ts[2]['owned_files'] = ['app/realtime.php', 'resources/js/realtime.ts']
    write(ts)
    assert validate.main(cfg, 0, quiet=True) == 0

def test_unknown_journey_step_is_a_defect(cfg, capsys):
    prep(cfg)
    ts = sound(); ts[2]['serves'] = ['J9.9']
    write(ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'unknown journey step' in capsys.readouterr().out

def test_an_endpoint_serving_no_journey_step_is_warned(cfg, capsys):
    prep(cfg)
    ts = sound(); ts[2]['serves'] = []
    write(ts)
    validate.main(cfg, 0, quiet=True)
    assert 'is anything going to call it' in capsys.readouterr().out

def test_a_missing_layer_is_a_defect(cfg, capsys):
    prep(cfg)
    ts = sound(); ts[1]['layer'] = None
    write(ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'declares no layer' in capsys.readouterr().out


# ---- backend-first ordering ----------------------------------------------

import yaml
from srashta import status as st_mod

def _phases(project, phases):
    c = yaml.safe_load(open('project.yaml'))
    c['phases'] = phases
    c['modules'] = {'identity': ['ACC'], 'notifications': ['NOT'], 'billing': ['BIL'],
                    'cross-cutting': ['NFR'], 'screens': ['SCR']}
    yaml.safe_dump(c, open('project.yaml', 'w'), sort_keys=False, width=100)

def _done(p):
    os.makedirs('contracts', exist_ok=True); os.makedirs('retrospectives', exist_ok=True)
    os.makedirs('build/tickets', exist_ok=True)
    os.makedirs(f'build/handoff/phase-{p}', exist_ok=True)
    open(f'contracts/phase-{p}.md','w').write('c')
    open(f'contracts/phase-{p}.approved','w').write('')
    json.dump([], open(f'build/tickets/phase-{p}.json','w'))
    open(f'retrospectives/phase-{p}.md','w').write('done')

BF = {0: {'name': 'API', 'layer': 'api', 'domains': ['ACC','NOT','NFR','BIL'], 'gate': 'g'},
      1: {'name': 'Screens', 'layer': 'surface', 'domains': ['SCR'], 'gate': 'g',
          'gate_artifacts': ['docs/openapi.yaml']}}

def setup_backend(project):
    _phases(project, BF)
    os.makedirs('spec', exist_ok=True); open('spec/s.md','w').write('spec')
    os.makedirs('build', exist_ok=True)
    json.dump([], open('build/requirements.json','w'))
    json.dump([], open('build/requirements.assigned.json','w'))

def test_brand_is_not_asked_for_while_backend_is_pending(project):
    setup_backend(project)
    cfg, s = st_mod.detect('.')
    who, what = st_mod.next_action(cfg, s)
    assert 'brand' not in what.lower()

def test_brand_is_asked_for_at_the_api_surface_boundary(project):
    setup_backend(project); _done(0)
    config = yaml.safe_load(open('project.yaml')); config['open_questions'] = {}
    yaml.safe_dump(config, open('project.yaml', 'w'))
    cfg, s = st_mod.detect('.')
    who, what = st_mod.next_action(cfg, s)
    assert 'endpoints are done' in what and 'brand-identity' in what

def test_design_system_follows_brand(project):
    setup_backend(project); _done(0)
    config = yaml.safe_load(open('project.yaml')); config['open_questions'] = {}
    yaml.safe_dump(config, open('project.yaml', 'w'))
    open('brand.yaml','w').write('product: x')
    cfg, s = st_mod.detect('.')
    assert 'design-system-bootstrap' in st_mod.next_action(cfg, s)[1]

def test_the_api_contract_gates_screen_decomposition(project):
    """Screens are designed against what exists, not against an imagined payload."""
    setup_backend(project); _done(0)
    config = yaml.safe_load(open('project.yaml')); config['open_questions'] = {}
    yaml.safe_dump(config, open('project.yaml', 'w'))
    open('brand.yaml','w').write('product: x'); open('DESIGN.md','w').write('tokens')
    cfg, s = st_mod.detect('.')
    who, what = st_mod.next_action(cfg, s)
    assert who == 'you' and 'docs/openapi.yaml' in what

def test_screens_decompose_once_the_contract_is_published(project):
    setup_backend(project); _done(0)
    config = yaml.safe_load(open('project.yaml')); config['open_questions'] = {}
    yaml.safe_dump(config, open('project.yaml', 'w'))
    open('brand.yaml','w').write('product: x'); open('DESIGN.md','w').write('tokens')
    os.makedirs('docs', exist_ok=True); open('docs/openapi.yaml','w').write('openapi: 3.1.0')
    cfg, s = st_mod.detect('.')
    assert 'phase-decomposition' in st_mod.next_action(cfg, s)[1]


def cfg_of():
    from srashta.common import load_project
    return load_project('project.yaml')

def test_no_ticket_may_own_the_generated_api_contract(project, capsys):
    """Per-ticket regeneration would collide across a wave. CI owns it instead."""
    _phases(project, BF)
    extract.main(cfg_of()); assign.main(cfg_of())
    ts = [t('C-01', ALL, layer='api'),
          t('T-01', ALL, ['C-01'], files=['app/x.php', 'docs/openapi.yaml'],
            layer='api', serves=['J1.1', 'J1.2'])]
    write(ts)
    assert validate.main(cfg_of(), 0, quiet=True) == 1
    assert 'No ticket may own it' in capsys.readouterr().out
