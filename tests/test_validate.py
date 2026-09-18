import json, os, pytest
from srashta import extract, assign, validate
from srashta.waves import finalise

def mk(project, tickets):
    extract.main(project and None or None) if False else None
    ts, _, _ = finalise(tickets)
    os.makedirs('build/tickets', exist_ok=True)
    json.dump(ts, open('build/tickets/phase-0.json', 'w'), indent=1)
    return ts

def t(id, reqs, deps=(), files=None, asserts=(), blocked=()):
    return dict(id=id, title=id, module='identity', depends_on=list(deps),
                owned_files=files or [f'app/{id}.php'], requirements=list(reqs),
                asserts=list(asserts), acceptance_tests=['x'], evidence=['y'],
                blocked_on=list(blocked), wave_hint=None, layer='api',
                serves=['J1.1', 'J1.2'])

ACC = ['FR-ACC-001', 'FR-ACC-002', 'FR-ACC-003', 'FR-ACC-004']
NOT = ['FR-NOT-001', 'FR-NOT-002']
NFR = ['NFR-001', 'NFR-002']

def good():
    return [t('C-01', ACC + NOT + NFR),
            t('T-01', ACC, ['C-01']), t('T-02', NOT, ['C-01']), t('T-03', NFR, ['C-01'])]

def prep(cfg):
    extract.main(cfg); assign.main(cfg)
    os.makedirs('contracts', exist_ok=True)
    open('contracts/phase-0.md','w').write('c'); open('contracts/phase-0.approved','w').write('')

def test_a_sound_graph_passes(cfg, capsys):
    prep(cfg); mk(None, good())
    assert validate.main(cfg, 0, quiet=True) == 0

def test_missing_owner_is_a_defect(cfg, capsys):
    prep(cfg)
    ts = good(); ts[1]['requirements'] = ['FR-ACC-001']      # 002-004 now unowned
    mk(None, ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'no feature ticket that owns it' in capsys.readouterr().out

def test_two_feature_owners_is_a_defect(cfg, capsys):
    prep(cfg)
    ts = good(); ts.append(t('T-04', ['FR-ACC-001'], ['C-01'], ['app/other.php']))
    mk(None, ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'feature owners' in capsys.readouterr().out

def test_file_collision_within_a_wave_is_a_defect(cfg, capsys):
    prep(cfg)
    ts = good(); ts[2]['owned_files'] = ts[1]['owned_files']
    mk(None, ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'both own' in capsys.readouterr().out

def test_glob_overlap_is_caught_not_just_equality(cfg, capsys):
    prep(cfg)
    ts = good()
    ts[1]['owned_files'] = ['app/Identity/*']
    ts[2]['owned_files'] = ['app/Identity/Thing.php']
    mk(None, ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'both own' in capsys.readouterr().out

def test_ticket_resting_on_no_contract_is_a_defect(cfg, capsys):
    prep(cfg)
    ts = [t('C-01', NFR), t('T-01', ACC), t('T-02', NOT, ['C-01']),
          t('T-03', NFR, ['C-01'], ['app/x.php'])]
    mk(None, ts)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'rests on no frozen contract' in capsys.readouterr().out

def test_undeclared_blocker_inheritance_is_a_defect(cfg, capsys):
    prep(cfg)
    ts = good(); ts[0]['blocked_on'] = ['OQ-01']
    fin, _, _ = finalise([dict(x) for x in ts])
    for x in fin:                                    # strip propagation to simulate a hand edit
        if x['id'] != 'C-01': x['blocked_on'] = []
    os.makedirs('build/tickets', exist_ok=True)
    json.dump(fin, open('build/tickets/phase-0.json', 'w'), indent=1)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'does not inherit' in capsys.readouterr().out

def test_hand_edited_derived_artifact_is_a_defect(cfg, capsys):
    prep(cfg); mk(None, good())
    r = json.load(open('build/requirements.json'))
    r[0]['text'] = 'TAMPERED'
    json.dump(r, open('build/requirements.json', 'w'), indent=1)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'hand-edited' in capsys.readouterr().out

def test_asserts_do_not_count_as_ownership(cfg, capsys):
    prep(cfg)
    ts = good(); ts[1]['requirements'] = ACC[:3]; ts[1]['asserts'] = [ACC[3]]
    mk(None, ts)
    assert validate.main(cfg, 0, quiet=True) == 1     # FR-ACC-004 asserted, owned by nobody
