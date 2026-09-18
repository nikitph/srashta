"""Every one of these reproduces a defect a review found in shipped code.

They were written before the fixes. Each asserts the tool no longer says
something false.
"""
import json, os, pytest
from types import SimpleNamespace
from srashta import extract, assign, validate, packs, events, run as run_mod
from srashta.eligible import eligible
from srashta.waves import finalise

ALL = ['FR-ACC-001','FR-ACC-002','FR-ACC-003','FR-ACC-004',
       'FR-NOT-001','FR-NOT-002','NFR-001','NFR-002']

def t(id, reqs=(), deps=(), files=None, layer='api', **kw):
    d = dict(id=id, title=id, module='identity', depends_on=list(deps),
             owned_files=files or [f'app/{id}.php'], requirements=list(reqs),
             asserts=[], acceptance_tests=['x'], evidence=['y'], blocked_on=[],
             wave_hint=None, layer=layer, serves=['J1.1','J1.2'])
    d.update(kw); return d

def write(ts, phase=0):
    fin, _, _ = finalise(ts)
    os.makedirs('build/tickets', exist_ok=True)
    json.dump(fin, open(f'build/tickets/phase-{phase}.json','w'), indent=1)
    return fin

def prep(cfg):
    extract.main(cfg); assign.main(cfg)
    os.makedirs('contracts', exist_ok=True)
    open('contracts/phase-0.md','w').write('contract design')
    open('contracts/phase-0.approved','w').write('')      # gate satisfied by default

# ---- 1. glob vs glob -------------------------------------------------------

def test_two_intersecting_globs_in_one_wave_are_a_defect(cfg, capsys):
    """app/Models/*.php and app/*/User.php both own app/Models/User.php.
    Neither fnmatches the other as a string, so the old check passed."""
    prep(cfg)
    write([t('C-01', ALL),
           t('T-01', ALL, ['C-01'], ['app/Models/*.php']),
           t('T-02', [], ['C-01'], ['app/*/User.php'])])
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'both own' in capsys.readouterr().out

def test_non_intersecting_globs_are_fine(cfg, capsys):
    prep(cfg)
    write([t('C-01', ALL),
           t('T-01', ALL, ['C-01'], ['app/Models/*.php']),
           t('T-02', [], ['C-01'], ['app/Actions/*.php'])])
    assert validate.main(cfg, 0, quiet=True) == 0

# ---- 2. cross-wave scheduling ---------------------------------------------

def test_the_next_wave_is_not_released_until_this_one_finishes():
    """A wave-1 ticket handed out while wave 0 is still in progress breaks the
    disjointness guarantee, which is only checked within a wave."""
    ts = finalise([t('C-01'), t('C-02'), t('T-01', deps=['C-02'])])[0]
    now, later, held = eligible(ts, {'C-02': 'merged', 'C-01': 'claimed'})
    assert [x['id'] for x in now] == []
    assert any(i == 'T-01' and 'wave' in r for i, r in held)

def test_the_next_wave_is_released_once_this_one_is_done():
    ts = finalise([t('C-01'), t('C-02'), t('T-01', deps=['C-02'])])[0]
    now, _, _ = eligible(ts, {'C-01': 'merged', 'C-02': 'merged'})
    assert [x['id'] for x in now] == ['T-01']

# ---- 3. bare excepts -------------------------------------------------------

def test_a_broken_shadow_run_does_not_silently_disable_drift_detection(cfg, capsys):
    prep(cfg)
    write([t('C-01', ALL), t('T-01', ALL, ['C-01'])])
    r = json.load(open('build/requirements.json')); r[0]['text'] = 'TAMPERED'
    json.dump(r, open('build/requirements.json','w'), indent=1)
    cfg['spec']['path'] = 'spec/does-not-exist.txt'       # shadow run cannot run
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'could not verify' in capsys.readouterr().out.lower()

def test_a_malformed_event_line_does_not_silently_drop_history(cfg, capsys):
    prep(cfg)
    write([t('C-01', ALL), t('T-01', ALL, ['C-01'])])
    events.append(cfg, 0, 'T-01', 'attempt_started')
    events.append(cfg, 0, 'T-01', 'tests_failed', {'tests': ['the single-use link']})
    with open(events.path(cfg, 0), 'a') as f:
        f.write('{truncated\n')
    with pytest.raises(SystemExit) as e:
        packs.main(cfg, 0)
    assert 'events' in str(e.value).lower()

# ---- 4. run propagation ----------------------------------------------------

def test_run_does_not_tick_a_stage_that_failed(cfg, capsys):
    """lint returns 1 rather than raising; the old run_step called that success."""
    import yaml
    s = open('spec/mini-prd.txt').read().replace(
        'FR-ACC-004 Sessions must expire after a defined period of inactivity.\nP1',
        'FR-ACC-004 Sessions must expire after a defined period of inactivity.')
    open('spec/mini-prd.txt','w').write(s)
    rc = run_mod.run(cfg)
    out = capsys.readouterr().out
    assert rc == 1
    assert '✓ Check spec quality' not in out

# ---- 5. duplicate pack block ----------------------------------------------

def test_the_brief_has_exactly_one_closing_block_and_no_dead_command(cfg, capsys):
    prep(cfg)
    write([t('C-01', ALL), t('T-01', ALL, ['C-01'])])
    packs.main(cfg, 0)
    p = open('build/context-packs/phase-0/T-01.md').read()
    assert p.count('If this brief is missing something') == 1
    assert 'srashta recall' not in p

# ---- 6. the approval gate --------------------------------------------------

def test_decomposition_is_refused_without_an_approved_contract(cfg, capsys):
    prep(cfg)
    os.remove('contracts/phase-0.approved')
    write([t('C-01', ALL), t('T-01', ALL, ['C-01'])])
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'approved' in capsys.readouterr().out.lower()

def test_packs_are_refused_without_an_approved_contract(cfg, capsys):
    prep(cfg)
    os.remove('contracts/phase-0.approved')
    write([t('C-01', ALL), t('T-01', ALL, ['C-01'])])
    with pytest.raises(SystemExit):
        packs.main(cfg, 0)

# ---- 7. derived waves ------------------------------------------------------

def test_a_hand_authored_wave_is_rejected(cfg, capsys):
    """finalise() is the only thing that derives waves. A tickets file that never
    went through it skips cycle detection and blocker propagation entirely."""
    prep(cfg)
    ts = [t('C-01', ALL), t('T-01', ALL, ['C-01'])]
    fin, _, _ = finalise([dict(x) for x in ts])
    for x in fin:
        x['wave'] = 0                 # hand-edited: both now claim wave 0
        x.pop('derived_by', None)
    json.dump(fin, open('build/tickets/phase-0.json','w'), indent=1)
    assert validate.main(cfg, 0, quiet=True) == 1
    out = capsys.readouterr().out.lower()
    assert 'derived' in out

# ---- 8. phase gate artifacts ----------------------------------------------

def test_a_phase_does_not_decompose_while_its_gate_artifact_is_missing(cfg, capsys):
    """FR-API-005. `status` reported an unmet gate and then let the decomposition
    happen anyway, so the gate was advice. Tickets written against an unpublished
    contract are written against a payload nobody has agreed to."""
    prep(cfg)
    cfg['phases'][0]['gate_artifacts'] = ['docs/openapi.yaml']
    write([t('C-01', ALL), t('T-01', ALL, ['C-01'])])
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'gate artifact' in capsys.readouterr().out

def test_a_phase_decomposes_once_its_gate_artifact_exists(cfg):
    prep(cfg)
    os.makedirs('docs', exist_ok=True)
    open('docs/openapi.yaml', 'w').write('openapi: 3.1.0\n')
    cfg['phases'][0]['gate_artifacts'] = ['docs/openapi.yaml']
    write([t('C-01', ALL), t('T-01', ALL, ['C-01'])])
    assert validate.main(cfg, 0, quiet=True) == 0

def test_a_surface_phase_before_an_api_phase_is_a_defect(cfg, capsys):
    """FR-MOD-011. The layer fields were read and never compared, so a phase plan that
    drew screens before the endpoints existed passed every check."""
    prep(cfg)
    cfg['phases'][0] = dict(cfg['phases'][0], layer='surface')
    cfg['phases'][1] = {'layer': 'api', 'gate': 'x'}
    write([t('C-01', ALL), t('T-01', ALL, ['C-01'])])
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'surface phase ordered before' in capsys.readouterr().out

# ---- 9. the CLI surface matches the package ------------------------------------

def test_every_subcommand_dispatches_to_a_module_that_exists():
    """`recall` was deleted; its parser entry and its dispatch line were not. The
    command crashed on import and --help advertised the query surface FR-BRF-005
    forbids. The old test asserted the MODULE was gone, which it was."""
    import re, importlib.util, srashta
    src = open(os.path.join(os.path.dirname(srashta.__file__), 'cli.py')).read()
    missing = [m for m in set(re.findall(r"import_module\('\.(\w+)'", src))
               if importlib.util.find_spec(f'srashta.{m}') is None]
    assert not missing, f"cli dispatches to modules that do not exist: {missing}"

def test_the_help_advertises_no_query_capability():
    import srashta
    src = open(os.path.join(os.path.dirname(srashta.__file__), 'cli.py')).read()
    assert 'recall' not in src

# ---- 10. a rule needs a command behind it ---------------------------------------

def test_an_authored_graph_becomes_valid_by_running_waves(cfg, capsys):
    """The validator rejects an unstamped graph (DEF-08) and no command could produce
    a stamped one, so an authored decomposition had no way forward at all."""
    from srashta import waves as waves_mod
    prep(cfg)
    raw = [t('C-01', ALL), t('T-01', ALL, ['C-01'])]
    for x in raw:                          # exactly what a planning agent writes
        x.pop('wave', None); x.pop('derived_by', None)
    os.makedirs('build/tickets', exist_ok=True)
    json.dump(raw, open('build/tickets/phase-0.json', 'w'), indent=1)
    assert validate.main(cfg, 0, quiet=True) == 1
    capsys.readouterr()

    assert waves_mod.main(cfg, 0) == 0
    assert 'next: srashta packs 0' in capsys.readouterr().out
    assert validate.main(cfg, 0, quiet=True) == 0

def test_waves_reports_the_edges_it_added_for_a_shared_resource(cfg, capsys):
    from srashta import waves as waves_mod
    prep(cfg)
    cfg['shared_resources'] = {'routes': {'paths': ['routes/api.php'],
                                          'strategy': 'serialise'}}
    raw = [t('C-01', ALL),
           t('T-01', ALL, ['C-01'], touches=['routes']),
           t('T-02', [], ['C-01'], files=['app/T-02.php'], touches=['routes'])]
    for x in raw:
        x.pop('wave', None); x.pop('derived_by', None)
    json.dump(raw, open('build/tickets/phase-0.json', 'w'), indent=1)
    assert waves_mod.main(cfg, 0) == 0
    out = capsys.readouterr().out
    assert "both touch 'routes'" in out
    assert validate.main(cfg, 0, quiet=True) == 0

# ---- 11. the version pin must not block its own remedy --------------------------

def test_upgrade_runs_on_a_project_pinned_to_another_version(project, capsys, monkeypatch):
    """The guard told the operator to run `srashta upgrade`, and then blocked it. A
    pinned project could never be migrated by the tool that pinned it."""
    import yaml
    from srashta import cli
    c = yaml.safe_load(open('project.yaml'))
    c['srashta_version'] = '0.0.1'
    yaml.safe_dump(c, open('project.yaml', 'w'), sort_keys=False)
    assert cli.main(['upgrade']) == 0
    assert yaml.safe_load(open('project.yaml'))['srashta_version'] != '0.0.1'

def test_a_pinned_project_still_refuses_to_validate(project, capsys):
    import yaml, pytest as _pt
    from srashta import cli
    c = yaml.safe_load(open('project.yaml'))
    c['srashta_version'] = '0.0.1'
    yaml.safe_dump(c, open('project.yaml', 'w'), sort_keys=False)
    with _pt.raises(SystemExit):
        cli.main(['validate', '0'])
