from srashta.eligible import eligible
from srashta.waves import finalise

def t(id, deps=(), blocked=()):
    return dict(id=id, title=id, module='m', depends_on=list(deps),
                owned_files=[f'src/{id}'], requirements=[], acceptance_tests=['x'],
                evidence=['y'], blocked_on=list(blocked), wave_hint=None)

def graph():
    ts, _, _ = finalise([t('C-01'), t('C-02'), t('C-03', ['C-01', 'C-02']),
                      t('T-01', ['C-03']), t('T-02', ['C-03'], blocked=['OQ-01'])])
    return ts

def test_lowest_wave_only_and_all_concurrent():
    now, later, held = eligible(graph(), {})
    assert {x['id'] for x in now} == {'C-01', 'C-02'}
    assert {i for i, _ in held} == {'C-03', 'T-01', 'T-02'}

def test_advances_as_work_merges():
    now, _, _ = eligible(graph(), {'C-01': 'merged', 'C-02': 'merged'})
    assert [x['id'] for x in now] == ['C-03']

def test_blocked_is_never_claimable_even_when_deps_are_met():
    state = {'C-01': 'merged', 'C-02': 'merged', 'C-03': 'merged'}
    now, _, held = eligible(graph(), state)
    assert [x['id'] for x in now] == ['T-01']
    assert ('T-02', 'blocked on OQ-01') in held

def test_in_progress_is_not_reoffered():
    now, _, _ = eligible(graph(), {'C-01': 'in_progress'})
    assert [x['id'] for x in now] == ['C-02']
