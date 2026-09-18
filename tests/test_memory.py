"""Never ask an agent to remember: put it in the artifact it reads.

Two things the pack used to omit — what the last attempt hit, and which choices were
already settled — so a retrying agent rediscovered the failure and a fresh one
helpfully reimplemented the rejected alternative.
"""
import json, os, yaml
from srashta import extract, assign, packs, events
from srashta.waves import finalise

ALL = ['FR-ACC-001','FR-ACC-002','FR-ACC-003','FR-ACC-004',
       'FR-NOT-001','FR-NOT-002','NFR-001','NFR-002']

def build(cfg):
    extract.main(cfg); assign.main(cfg)
    os.makedirs('contracts', exist_ok=True)
    open('contracts/phase-0.md','w').write('c'); open('contracts/phase-0.approved','w').write('')
    ts, _, _ = finalise([
        dict(id='C-01', title='c', module='identity', depends_on=[], owned_files=['app/c.php'],
             requirements=ALL, asserts=[], acceptance_tests=['x'], evidence=['y'],
             blocked_on=[], wave_hint=None, layer='api', serves=['J1.1','J1.2']),
        dict(id='T-01', title='Password reset', module='identity', depends_on=['C-01'],
             owned_files=['app/t.php'], requirements=ALL, asserts=[],
             acceptance_tests=['the link is single-use', 'sessions are invalidated'],
             evidence=['y'], blocked_on=[], wave_hint=None, layer='api',
             serves=['J1.1','J1.2'])])
    os.makedirs('build/tickets', exist_ok=True)
    json.dump(ts, open('build/tickets/phase-0.json','w'), indent=1)

def pack(name='T-01'):
    return open(f'build/context-packs/phase-0/{name}.md').read()

def test_a_clean_ticket_carries_no_history(cfg, capsys):
    build(cfg); packs.main(cfg, 0)
    assert 'previous attempt' not in pack()

def test_a_retry_carries_the_failures_it_already_hit(cfg, capsys):
    build(cfg)
    events.append(cfg, 0, 'T-01', 'attempt_started', agent='codex')
    events.append(cfg, 0, 'T-01', 'tests_failed', {'tests': ['the link is single-use']})
    packs.main(cfg, 0)
    p = pack()
    assert 'What the previous attempt hit  (attempt 2)' in p
    assert 'the link is single-use' in p

def test_an_out_of_scope_touch_is_named_as_a_decomposition_defect(cfg, capsys):
    build(cfg)
    events.append(cfg, 0, 'T-01', 'attempt_started')
    events.append(cfg, 0, 'T-01', 'out_of_scope_touch', {'files': ['app/Models/User.php']})
    packs.main(cfg, 0)
    p = pack()
    assert 'app/Models/User.php' in p and 'ownership is wrong' in p

def test_history_is_dropped_once_the_ticket_merged(cfg, capsys):
    build(cfg)
    events.append(cfg, 0, 'T-01', 'attempt_started')
    events.append(cfg, 0, 'T-01', 'tests_failed', {'tests': ['x']})
    events.append(cfg, 0, 'T-01', 'merged', {'diff_lines': 10})
    packs.main(cfg, 0)
    assert 'previous attempt' not in pack()

def test_settled_decisions_reach_the_tickets_they_constrain(cfg, capsys):
    cfg['decisions'] = {'D-01': {
        'decision': 'Payment is taken in full at purchase.',
        'rejected': 'Authorise-and-capture — a failed-payment path at the end of every trial.',
        'constrains': ['identity']}}
    build(cfg); packs.main(cfg, 0)
    p = pack()
    assert 'do not re-litigate' in p.lower()
    assert 'Authorise-and-capture' in p
    assert 'do not quietly implement the alternative' in p

def test_a_decision_constraining_something_else_is_not_carried(cfg, capsys):
    cfg['decisions'] = {'D-01': {'decision': 'x', 'rejected': 'y', 'constrains': ['ledger']}}
    build(cfg); packs.main(cfg, 0)
    assert 're-litigate' not in pack()


# ---- pack_insufficient: the signal, with no capability attached ----------

def test_the_pack_tells_the_agent_how_to_report_a_gap(cfg, capsys):
    build(cfg); packs.main(cfg, 0)
    p = pack()
    assert 'If this brief is missing something' in p
    assert 'pack_insufficient' in p
    assert 'Do not read the specification' in p
    assert 'defect in the decomposition, not in you' in p

def test_a_reported_gap_is_recorded(cfg):
    build(cfg)
    events.append(cfg, 0, 'T-01', 'pack_insufficient',
                  {'needed': 'which mailer the reset link goes through'})
    d = events.derive(events.read(cfg, 0))['T-01']
    assert d['pack_gaps'] == ['which mailer the reset link goes through']

def test_the_same_gap_across_tickets_is_flagged_for_the_template(cfg, capsys):
    """One ticket needing something is a miss. Several is a template change."""
    build(cfg)
    for tid in ('T-01', 'C-01'):
        events.append(cfg, 0, tid, 'pack_insufficient', {'needed': 'the retention period'})
    from types import SimpleNamespace
    events.main(cfg, SimpleNamespace(summary=True, list_kinds=False, phase=0,
                                     ticket=None, kind=None, data=None, agent=None))
    out = capsys.readouterr().out
    assert 'could not proceed at all' in out
    assert 'belongs in the pack template' in out

def test_there_is_no_query_capability(cfg):
    """The fix for an insufficient brief is a better brief, not a lookup. A query
    surface erodes by reasonable-looking increments until the boundary is gone."""
    import srashta, pkgutil
    assert 'recall' not in {m.name for m in pkgutil.iter_modules(srashta.__path__)}
    assert 'memory_query' not in events.KINDS


# ---- brief feedback: the routine capture, required as evidence -------------

from srashta.waves import BRIEF_FEEDBACK, finalise
from srashta import validate

def test_every_ticket_requires_brief_feedback_as_evidence(cfg):
    """Injected, not authored — a required item nobody must remember."""
    ts, _, _ = finalise([dict(id='T-01', title='t', module='identity', depends_on=[],
                           owned_files=['app/t.php'], requirements=[], asserts=[],
                           acceptance_tests=['x'], evidence=['feature test output'],
                           blocked_on=[], wave_hint=None)])
    assert BRIEF_FEEDBACK in ts[0]['evidence']

def test_removing_it_is_a_validation_defect(cfg, capsys):
    build(cfg)
    ts = json.load(open('build/tickets/phase-0.json'))
    ts[1]['evidence'] = ['feature test output']          # stripped by hand
    json.dump(ts, open('build/tickets/phase-0.json','w'), indent=1)
    assert validate.main(cfg, 0, quiet=True) == 1
    assert 'does not require brief feedback' in capsys.readouterr().out

def test_the_pack_asks_for_an_honest_answer(cfg, capsys):
    build(cfg); packs.main(cfg, 0)
    p = pack()
    assert 'whether this brief was sufficient' in p
    assert 'had to infer' in p

def test_partial_answers_are_the_useful_ones(cfg, capsys):
    build(cfg)
    events.append(cfg, 0, 'T-01', 'brief_feedback',
                  {'sufficient': 'partial', 'note': 'inferred the retention period'})
    d = events.derive(events.read(cfg, 0))['T-01']
    assert d['brief_sufficient'] == 'partial'
    assert d['brief_notes'] == ['inferred the retention period']

def test_merging_without_answering_is_surfaced(cfg, capsys):
    """If the orchestrator is not recording it, the measurement is silently dead."""
    build(cfg)
    events.append(cfg, 0, 'T-01', 'attempt_started')
    events.append(cfg, 0, 'T-01', 'merged', {'diff_lines': 40})
    from types import SimpleNamespace
    events.main(cfg, SimpleNamespace(summary=True, list_kinds=False, phase=0,
                                     ticket=None, kind=None, data=None, agent=None))
    out = capsys.readouterr().out
    assert 'merged without answering' in out
    assert 'the orchestrator is not recording it' in out
