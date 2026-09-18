"""Cross-command regression tests for the actual trust and persistence boundaries."""
import copy
import json
import subprocess
import sys
from pathlib import Path
import pytest
import yaml
from srashta import approvals, extract, assign, tickets, packs, export, events, execution, phase, api
from srashta.common import write_json


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


@pytest.fixture
def plan(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    git('init', '-q'); git('config', 'user.email', 'fixture@example.invalid'); git('config', 'user.name', 'Fixture')
    for directory in ('spec', 'tickets', 'contracts', 'app', 'tests', 'retrospectives'):
        Path(directory).mkdir()
    Path('spec/prd.md').write_text('## FR-ACC-001 [P0] Return a value\n\nWHEN the action runs, THE SYSTEM SHALL return 42.\n')
    Path('.gitignore').write_text('__pycache__/\n')
    Path('constitution.md').write_text('Deterministic tests; no network calls.')
    Path('contracts/phase-0.md').write_text('VALUE is the integer 42; implementation imports app.contract.VALUE.')
    cfg = {'project': 'test', 'artifact_version': 2, 'out_dir': 'build',
           'spec': {'path': 'spec/prd.md'}, 'modules': {'identity': ['ACC']},
           'phases': {0: {'name': 'API', 'layer': 'api', 'domains': ['ACC']}},
           'overrides': {}, 'verification_commands': [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']]}
    Path('project.yaml').write_text(yaml.safe_dump(cfg))
    from srashta.common import load_project
    cfg = load_project()
    def ticket(tid, files, deps=(), reqs=()):
        return dict(id=tid,title=tid,module='identity',layer='api',depends_on=list(deps),owned_files=files,
                    requirements=list(reqs),acceptance_tests=['the action returns 42'],evidence=['passing test output'])
    graph = [ticket('C-01',['app/contract.py','tests/test_contract.py']), ticket('T-01',['app/action.py','tests/test_action.py'],['C-01'],['FR-ACC-001'])]
    graph[0]['contract_context'] = 'VALUE is the integer 42; implementation imports app.contract.VALUE.'
    write_json('tickets/phase-0.json', graph)
    extract.main(cfg); assign.main(cfg); approvals.approve(cfg, 0, 'Fixture reviewer'); tickets.write(cfg,0)
    packs.main(cfg,0); export.run(cfg,0)
    git('add','.'); git('commit','-qm','Approved fixture plan')
    return cfg


def test_source_survives_full_build_deletion(plan):
    import shutil
    before = Path('tickets/phase-0.json').read_bytes()
    shutil.rmtree('build')
    extract.main(plan); assign.main(plan); tickets.write(plan,0); packs.main(plan,0); export.run(plan,0)
    assert Path('tickets/phase-0.json').read_bytes() == before
    manifest=json.loads(Path('build/handoff/phase-0/manifest.json').read_text())
    assert manifest['context_packs'] == 'packs/<TICKET_ID>.md'
    assert manifest['pack_sha256']['T-01.md'] == approvals.digest('build/handoff/phase-0/packs/T-01.md')


def test_stale_export_fails_without_replacing_handoff(plan):
    previous=Path('build/handoff/phase-0/manifest.json').read_bytes()
    Path('build/context-packs/phase-0/T-01.md').write_text('tampered')
    with pytest.raises(ValueError,match='stale'): export.run(plan,0)
    assert Path('build/handoff/phase-0/manifest.json').read_bytes()==previous


def test_source_drift_refuses_packs(plan):
    raw=json.loads(Path('tickets/phase-0.json').read_text()); raw[1]['title']='changed judgment'
    write_json('tickets/phase-0.json',raw)
    with pytest.raises(ValueError,match='authored source'): packs.main(plan,0)


def test_failed_checks_cannot_supply_merge_evidence(plan):
    base=git('rev-parse','HEAD')
    Path('app/contract.py').write_text('VALUE=42\n')
    git('add','app/contract.py');git('commit','-qm','C-01: contract')
    with pytest.raises((OSError,ValueError)):
        events.append(plan,0,'C-01','merged',{'head':git('rev-parse','HEAD'),'reviewed_by':'Fixture reviewer'})
    assert not Path(execution.evidence_path(plan,0,'C-01')).exists()


def test_verified_ticket_lifecycle_and_phase_close(plan):
    for ticket, contents in [('C-01', {'app/contract.py':'VALUE=42\n','tests/test_contract.py':'import unittest\nfrom app.contract import VALUE\nclass TestContract(unittest.TestCase):\n    def test_value(self): self.assertEqual(VALUE,42)\n'}),
          ('T-01', {'app/action.py':'from app.contract import VALUE\ndef run(): return VALUE\n',
                    'tests/test_action.py':'import unittest\nfrom app.action import run\nclass TestAction(unittest.TestCase):\n    def test_result(self): self.assertEqual(run(),42)\n'})]:
        base=git('rev-parse','HEAD')
        for name,body in contents.items(): Path(name).write_text(body)
        git('add',*contents); git('commit','-qm',f'{ticket}: implementation')
        execution.verify(plan,0,ticket,base)
        events.append(plan,0,ticket,'brief_feedback',{'sufficient':True})
        events.append(plan,0,ticket,'merged',{'head':git('rev-parse','HEAD'),'reviewed_by':'Fixture reviewer'})
        git('add','evidence','events');git('commit','-qm','Record execution evidence')
    Path('retrospectives/phase-0.md').write_text('Both briefs were sufficient; no changes to planning required.')
    assert phase.close(plan,0,'Fixture reviewer')==0
    assert phase.closed(plan,0)
    Path('contracts/phase-0.md').write_text('Changed contract')
    assert not phase.closed(plan,0)


def test_feature_cannot_modify_frozen_contract(plan):
    base=git('rev-parse','HEAD')
    Path('app/contract.py').write_text('VALUE=43\n')
    git('add','app/contract.py');git('commit','-qm','T-01: sneak contract mutation')
    with pytest.raises(ValueError,match='unowned or frozen'): execution.inspect_diff(plan,0,'T-01',base)


def test_candidate_cannot_expand_its_ownership(plan):
    base=git('rev-parse','HEAD')
    graph=json.loads(Path('build/tickets/phase-0.json').read_text()); graph[1]['owned_files']=['**']
    write_json('build/tickets/phase-0.json',graph)
    Path('constitution.md').write_text('anything goes')
    git('add','.');git('commit','-qm','T-01: enlarge ownership')
    with pytest.raises(ValueError,match='unowned or frozen'): execution.inspect_diff(plan,0,'T-01',base)


def test_event_retry_is_idempotent(plan):
    first=events.append(plan,0,'T-01','attempt_started',event_id='attempt-1')
    assert events.append(plan,0,'T-01','attempt_started',event_id='attempt-1')==first
    assert len(events.read(plan,0))==1
    with pytest.raises(ValueError,match='reused'): events.append(plan,0,'T-01','blocked',event_id='attempt-1')


def test_busy_ticket_is_not_reported_complete():
    from srashta.eligible import eligible
    ready,later,held=eligible([{'id':'C-01','wave':0,'blocked_on':[],'depends_on':[]}],{'C-01':'in_review'})
    assert held==[('C-01','in_review')]
    with pytest.raises(ValueError): eligible([{'id':'C-01'}],{'C-01':'completed'})


@pytest.mark.parametrize('attack',['output','marker_removed','marker_changed'])
def test_freeze_uses_trusted_base(plan, attack):
    import hashlib
    doc={'openapi':'3.1.0','info':{'title':'Fixture','version':'1'},'paths':{'/items':{'get':{'responses':{'200':{'description':'ok'}}}}}}
    Path('docs').mkdir(); Path('docs/openapi.yaml').write_text(yaml.safe_dump(doc))
    write_json(api.MARKER,{'openapi_sha256':hashlib.sha256(api.canonical(yaml.safe_dump(doc)).encode()).hexdigest()})
    git('add','docs');git('commit','-qm','Freeze fixture');base=git('rev-parse','HEAD')
    doc['paths']['/extra']={}
    candidate=json.dumps(doc)
    plan['api_generate']=[sys.executable,'-c','from pathlib import Path; import sys; Path(sys.argv[1]).write_text(sys.argv[2])','{output}',candidate]
    if attack=='output': Path('docs/openapi.yaml').write_text(candidate)
    elif attack=='marker_removed': Path(api.MARKER).unlink()
    else: write_json(api.MARKER,{'openapi_sha256':hashlib.sha256(api.canonical(candidate).encode()).hexdigest()})
    with pytest.raises(ValueError,match='frozen|freeze'): api.run(plan,'check',base)


def test_worker_omits_spec_history_other_briefs_and_secrets(plan,tmp_path):
    from srashta.worker import run
    Path('app/visible.py').write_text('code')
    Path('.env').write_text('SECRET=do-not-export')
    git('add','app/visible.py','.env');git('commit','-qm','Fixture input')
    destination=tmp_path/'worker'
    run(plan,0,'T-01',str(destination))
    assert (destination/'BRIEF.md').exists()
    assert (destination/'app/visible.py').exists()
    assert not (destination/'.git').exists()
    assert not (destination/'spec').exists()
    assert not (destination/'build').exists()
    assert not (destination/'.env').exists()


def test_emitted_artifacts_match_the_shipped_schemas(plan):
    import jsonschema
    from importlib.resources import files
    base=files('srashta')/'templates/schemas'
    for kind, path in [('ticket','build/tickets/phase-0.json'),('requirement','build/requirements.assigned.json')]:
        schema=json.loads((base/f'{kind}.schema.json').read_text())
        for row in json.loads(Path(path).read_text()): jsonschema.validate(row,schema)


def test_trace_finds_requirement_and_commit(plan,capsys):
    from srashta import trace
    Path('app/action.py').write_text('x=42')
    git('add','app/action.py');git('commit','-qm','T-01: action')
    assert trace.main(plan,'FR-ACC-001')==0
    assert 'T-01: action' in capsys.readouterr().out
    assert trace.main(plan,git('rev-parse','HEAD'))==0
    assert 'EXISTS BECAUSE OF' in capsys.readouterr().out


def test_unknown_event_contract_schema_blocks_export(plan):
    plan['events']={'note.created':{'listeners':['audit']}}
    with pytest.raises(ValueError,match='payload schema'): export.run(plan,0)
