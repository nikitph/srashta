import importlib
import json
import subprocess
from pathlib import Path
import pytest
from srashta import assign, dsm, lint, trace


def test_init_never_overwrites_existing_work(tmp_path):
    root=tmp_path/'existing';root.mkdir();(root/'mine').write_text('preserve')
    with pytest.raises(ValueError,match='not empty'): importlib.import_module('srashta.init').run('demo',str(root),'none')
    assert (root/'mine').read_text()=='preserve'


def test_init_hooks_work_after_clone(tmp_path):
    root=tmp_path/'initial'
    init=importlib.import_module('srashta.init');init.run('demo',str(root),'none')
    def git(cwd,*args): return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
    git(root,'config','user.name','Fixture');git(root,'config','user.email','fixture@example.invalid')
    git(root,'add','.');git(root,'commit','-qm','Initial')
    clone=tmp_path/'clone';git(tmp_path,'clone','-q',str(root),str(clone));init.bootstrap(clone)
    git(clone,'config','user.name','Fixture');git(clone,'config','user.email','fixture@example.invalid')
    git(clone,'checkout','-qb','T-01-example');(clone/'sample').write_text('x')
    git(clone,'add','sample');git(clone,'commit','-qm','Implement')
    assert git(clone,'log','-1','--format=%s').startswith('T-01:')
    assert (clone/'.agents/skills/phase-decomposition/SKILL.md').exists()
    assert (clone/'.github/workflows/srashta.yml').exists()


def test_scaffold_failure_does_not_create_a_partial_project(tmp_path,monkeypatch):
    init=importlib.import_module('srashta.init')
    def fail(*args): raise RuntimeError('scaffold failed')
    monkeypatch.setattr(init,'scaffold',fail)
    root=tmp_path/'demo'
    with pytest.raises(RuntimeError): init.run('demo',str(root),'laravel-react',True)
    assert not root.exists()


def test_lint_distinguishes_smells_and_missing_structure():
    rows=[{'id':'FR-ACC-001','domain':'ACC','priority':None,'text':'It must be fast and user-friendly.','criteria':['Do a thing.']}]
    findings=lint.lint(rows,{})
    assert 'ambiguous' in findings and 'subjective' in findings and 'non_ears_criterion' in findings
    errors,_=lint.structure(rows,{'modules':{},'phases':{}})
    assert any('no priority' in e for e in errors) and any('orphaned' in e for e in errors)


def test_dsm_reads_cross_references_in_criteria_and_degrades():
    cfg={'spec':{'id_pattern':r'FR-[A-Z]+-\d{3}'}}
    rows=[{'id':'FR-AA-001','text':'First','criteria':['WHEN ready THE SYSTEM SHALL call FR-BB-001.']},
          {'id':'FR-BB-001','text':'Second','criteria':[]}]
    edges,_=dsm.build(cfg,rows)
    assert edges[('FR-AA-001','FR-BB-001')]>0
    assert dsm.confidence(rows,[{},{}],[],{'a','b'})=='low'


def test_duplicate_module_assignment_is_a_defect(cfg):
    from srashta import extract
    extract.main(cfg);cfg['modules']['another']=['ACC']
    with pytest.raises(SystemExit,match='multiple modules'):assign.main(cfg)


def test_invalid_terminal_transition_is_rejected(tmp_path):
    from srashta.gentests import generate
    with pytest.raises(SystemExit,match='terminal'):
        generate({'item':{'states':['done'],'terminal':['done'],'transitions':[{'from':'done','to':'done'}]}},outdir=str(tmp_path))


def test_default_guard_runs_and_rejects_production(tmp_path,monkeypatch):
    import shutil
    if not shutil.which('php'): pytest.skip('PHP integration runtime unavailable')
    from importlib.resources import files
    from srashta.defaults import generate
    monkeypatch.chdir(tmp_path);Path('config').mkdir()
    Path('config/defaults.yaml').write_text('retention:\n  days: 30\n')
    generate({'open_questions':{'OQ-1':{'kind':'blocker','config_key':'retention.days','answered':False}}})
    Path('Guard.php').write_text((files('srashta')/'templates/laravel/ProvisionalConfig.php').read_text())
    Path('probe.php').write_text('''<?php
$cfg = require 'config/srashta.php';
function config($key, $default=null) { global $cfg;
    $value=$cfg; foreach(array_slice(explode('.', $key),1) as $part) { $value=$value[$part] ?? $default; } return $value;
}
function app() { return new class { function environment($allowed) { return in_array(getenv('APP_ENV'), $allowed, true); } }; }
require 'Guard.php';
try { echo App\\Support\\ProvisionalConfig::read('retention.days', true); } catch (RuntimeException $e) { exit(7); }
''')
    import os
    assert subprocess.run(['php','probe.php'],env={**os.environ,'APP_ENV':'production'}).returncode==7
    local=subprocess.run(['php','probe.php'],env={**os.environ,'APP_ENV':'testing'},capture_output=True,text=True)
    assert local.returncode==0 and local.stdout=='30'
