from srashta import events

def test_counts_are_derived_never_stored(cfg):
    events.append(cfg, 0, 'T-08', 'attempt_started', agent='codex')
    events.append(cfg, 0, 'T-08', 'tests_failed', {'tests': ['a', 'b']})
    events.append(cfg, 0, 'T-08', 'attempt_started', agent='codex')
    events.append(cfg, 0, 'T-08', 'merged', {'diff_lines': 240})
    d = events.derive(events.read(cfg, 0))['T-08']
    assert d['attempts'] == 2
    assert d['first_run_test_failures'] == 2
    assert d['failed_tests'] == ['a', 'b']
    assert d['merged'] and d['diff_lines'] == 240 and d['agent'] == 'codex'

def test_log_is_append_only(cfg):
    events.append(cfg, 0, 'T-01', 'attempt_started')
    first = open(events.path(cfg, 0)).read()
    events.append(cfg, 0, 'T-02', 'attempt_started')
    assert open(events.path(cfg, 0)).read().startswith(first)

def test_unknown_kind_is_rejected_at_write_time(cfg):
    import pytest
    with pytest.raises(SystemExit) as e:
        events.append(cfg, 0, 'T-01', 'vibes')
    assert 'unknown event kind' in str(e.value)

def test_unknown_kind_in_an_old_log_is_ignored_when_deriving(cfg):
    """Append-only means an older log must stay readable by a newer srashta."""
    events.append(cfg, 0, 'T-01', 'attempt_started')
    with open(events.path(cfg, 0), 'a') as f:
        f.write('{"ts":"x","ticket":"T-01","kind":"from_the_future"}\n')
    assert events.derive(events.read(cfg, 0))['T-01']['attempts'] == 1

def test_failures_after_the_first_attempt_are_not_first_run(cfg):
    events.append(cfg, 0, 'T-01', 'attempt_started')
    events.append(cfg, 0, 'T-01', 'tests_failed', {'tests': ['a']})
    events.append(cfg, 0, 'T-01', 'attempt_started')
    events.append(cfg, 0, 'T-01', 'tests_failed', {'tests': ['b', 'c']})
    d = events.derive(events.read(cfg, 0))['T-01']
    assert d['attempts'] == 2 and d['first_run_test_failures'] == 1
