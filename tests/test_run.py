"""End-to-end through the same entry point the CLI uses.

The chain is imported dynamically, so a broken import in one stage is invisible
until that stage runs. These tests exercise every stage for real.
"""
import json, os
from srashta import run, extract, assign
from srashta.waves import finalise

def test_chain_runs_clean(cfg, capsys):
    assert run.run(cfg) == 0
    out = capsys.readouterr().out
    for stage in ('Parse the spec', 'Check spec quality',
                  'Derive modules and flows', 'Assign phases'):
        assert stage in out
    assert os.path.exists('build/requirements.assigned.json')

def test_chain_reaches_packs_and_the_gate(cfg, capsys):
    extract.main(cfg); assign.main(cfg)
    os.makedirs('contracts', exist_ok=True)
    open('contracts/phase-0.md','w').write('c'); __import__('srashta.approvals', fromlist=['approve']).approve(cfg, 0, 'test reviewer')
    ts, _, _ = finalise([
        dict(id='C-01', title='c', module='identity', depends_on=[],
             owned_files=['app/c.php'], layer='api', serves=['J1.1','J1.2'],
             requirements=['FR-ACC-001','FR-ACC-002','FR-ACC-003','FR-ACC-004',
                           'FR-NOT-001','FR-NOT-002','NFR-001','NFR-002'],
             asserts=[], acceptance_tests=['x'], evidence=['y'], blocked_on=[],
             wave_hint=None),
        dict(id='T-01', title='t', module='identity', depends_on=['C-01'],
             owned_files=['app/t.php'], layer='api', serves=['J1.1','J1.2'],
             requirements=['FR-ACC-001','FR-ACC-002','FR-ACC-003','FR-ACC-004',
                           'FR-NOT-001','FR-NOT-002','NFR-001','NFR-002'],
             asserts=[], acceptance_tests=['x'], evidence=['y'], blocked_on=[],
             wave_hint=None)])
    os.makedirs('build/tickets', exist_ok=True)
    json.dump(ts, open('build/tickets/phase-0.json','w'), indent=1)
    assert run.run(cfg, phase=0) == 0
    out = capsys.readouterr().out
    assert 'context packs' in out and 'Validate ticket graph' in out
    assert os.path.isdir('build/context-packs/phase-0')

def test_a_blocker_gating_phase_zero_is_surfaced(cfg, capsys):
    cfg['open_questions']['OQ-01']['gates_phase'] = 0
    run.run(cfg)
    assert 'Waiting on you: OQ-01' in capsys.readouterr().out
