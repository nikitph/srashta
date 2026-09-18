import pytest
from srashta.waves import finalise

def t(id, deps=(), files=None, wave_hint=None, blocked=()):
    return dict(id=id, title=id, module='m', depends_on=list(deps),
                owned_files=files or [f'src/{id}.php'], requirements=[],
                acceptance_tests=['x'], evidence=['y'],
                blocked_on=list(blocked), wave_hint=wave_hint)

def test_waves_are_derived_from_the_graph_not_the_hint():
    ts, drift, _ = finalise([t('C-01'), t('C-02', ['C-01'], wave_hint=0),
                          t('T-01', ['C-02'], wave_hint=0)])
    by = {x['id']: x for x in ts}
    assert (by['C-01']['wave'], by['C-02']['wave'], by['T-01']['wave']) == (0, 1, 2)
    assert len(drift) == 2          # both hints were wrong and are reported

def test_longest_path_not_shortest():
    """A ticket depending on both a root and a deep node sits after the deep one."""
    ts, _, _ = finalise([t('C-01'), t('C-02', ['C-01']), t('T-01', ['C-01', 'C-02'])])
    assert {x['id']: x['wave'] for x in ts}['T-01'] == 2

def test_cycle_is_fatal():
    with pytest.raises(SystemExit) as e:
        finalise([t('A', ['B']), t('B', ['A'])])
    assert 'cycle' in str(e.value)

def test_unknown_dependency_is_fatal():
    with pytest.raises(SystemExit) as e:
        finalise([t('A', ['NOPE'])])
    assert 'unknown ticket' in str(e.value)

def test_blockers_propagate_down_the_graph():
    ts, _, _ = finalise([t('C-01', blocked=['OQ-01']), t('T-01', ['C-01']),
                      t('I-01', ['T-01']), t('T-99')])
    by = {x['id']: x['blocked_on'] for x in ts}
    assert by['C-01'] == by['T-01'] == by['I-01'] == ['OQ-01']
    assert by['T-99'] == []          # unrelated ticket is untouched

def test_kind_is_inferred_from_the_id():
    ts, _, _ = finalise([t('C-01'), t('T-01', ['C-01']), t('I-01', ['T-01'])])
    assert [x['kind'] for x in ts] == ['contract', 'feature', 'integration']
