import os, json, subprocess
import pytest
from types import SimpleNamespace
from srashta import skills

SK = '.claude/skills'

@pytest.fixture(autouse=True)
def isolated_git_identity(monkeypatch):
    """Promotion commits in a fresh clone must not use the developer's identity."""
    for role in ('AUTHOR', 'COMMITTER'):
        monkeypatch.setenv(f'GIT_{role}_NAME', 'Srashta test fixture')
        monkeypatch.setenv(f'GIT_{role}_EMAIL', 'fixture@example.invalid')

def args(**kw):
    return SimpleNamespace(full=kw.get('full', False), sync=kw.get('sync', False),
                           force=kw.get('force', False), promote=kw.get('promote', None))

def seed():
    os.makedirs(SK, exist_ok=True)
    for name, body in skills._blueprint().items():
        open(os.path.join(SK, name), 'w').write(body)

def edit(name='spec-authoring.md', line='HOUSE RULE: cap requirements at 300.'):
    open(os.path.join(SK, name), 'a').write(f'\n{line}\n')

def test_reports_when_in_sync(project, capsys):
    seed()
    assert skills.main(args()) == 0
    assert 'match the blueprint' in capsys.readouterr().out

def test_detects_a_local_edit(project, capsys):
    seed(); edit()
    skills.main(args())
    out = capsys.readouterr().out
    assert 'spec-authoring.md' in out and 'sync would add 0, remove 2' in out

def test_sync_refuses_without_naming_what_it_discards(project, capsys):
    """The real hazard is the overwrite, not the timing."""
    seed(); edit()
    assert skills.main(args(sync=True)) == 1
    out = capsys.readouterr().out
    assert 'would be DISCARDED' in out
    assert 'HOUSE RULE: cap requirements at 300.' in out     # quotes the actual line
    assert 'promote' in out

def test_force_syncs_and_discards(project, capsys):
    seed(); edit()
    assert skills.main(args(sync=True, force=True)) == 0
    assert 'HOUSE RULE' not in open(os.path.join(SK, 'spec-authoring.md')).read()

def test_sync_never_deletes_a_project_only_skill(project, capsys):
    seed(); edit()
    open(os.path.join(SK, 'deploy-notes.md'), 'w').write('ours only')
    skills.main(args(sync=True, force=True))
    assert os.path.exists(os.path.join(SK, 'deploy-notes.md'))

def test_a_new_blueprint_skill_syncs_cleanly(project, capsys):
    seed(); os.remove(os.path.join(SK, 'brand-identity.md'))
    assert skills.main(args(sync=True)) == 0          # nothing to discard, no refusal
    assert os.path.exists(os.path.join(SK, 'brand-identity.md'))

def test_promote_needs_a_configured_repo(project, capsys):
    seed(); edit()
    assert skills.main(args(promote=[]), cfg={'project': 'mini'}) == 1
    assert 'no blueprint repo configured' in capsys.readouterr().out

def test_promote_with_nothing_changed_is_a_noop(project, capsys):
    seed()
    assert skills.main(args(promote=[]), cfg={'blueprint_repo': '/nope'}) == 0
    assert 'nothing to promote' in capsys.readouterr().out

def _fake_gh(tmp_path, monkeypatch):
    d = tmp_path / 'bin'; d.mkdir(exist_ok=True)
    gh = d / 'gh'
    gh.write_text('#!/bin/sh\necho "$@" > %s/gh-args.txt\n'
                  'echo https://example.test/pull/1\n' % tmp_path)
    gh.chmod(0o755)
    monkeypatch.setenv('PATH', f"{d}:{os.environ['PATH']}")
    return tmp_path / 'gh-args.txt'

def _blueprint_repo(tmp_path):
    origin = tmp_path / 'origin'
    subprocess.run(['git', 'init', '-q', '--bare', str(origin)], check=True)
    work = tmp_path / 'work'
    subprocess.run(['git', 'clone', '-q', str(origin), str(work)], check=True)
    d = work / skills.TEMPLATE_PATH; d.mkdir(parents=True)
    for n, b in skills._blueprint().items(): (d / n).write_text(b)
    env = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t',
           'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}
    subprocess.run(['git', 'add', '-A'], cwd=work, check=True, env=env)
    subprocess.run(['git', 'commit', '-q', '-m', 'init'], cwd=work, check=True, env=env)
    subprocess.run(['git', 'push', '-q', 'origin', 'HEAD:main'], cwd=work, check=True, env=env)
    subprocess.run(['git', '--git-dir', str(origin), 'symbolic-ref', 'HEAD',
                    'refs/heads/main'], check=True)
    return origin

def test_promote_opens_a_pr_carrying_the_diff(project, tmp_path, capsys, monkeypatch):
    seed(); edit()
    argsfile = _fake_gh(tmp_path, monkeypatch)
    origin = _blueprint_repo(tmp_path)
    rc = skills.main(args(promote=[]), cfg={'project': 'mini', 'blueprint_repo': str(origin)})
    assert rc == 0
    out = capsys.readouterr().out
    assert 'opened a pull request' in out
    body = argsfile.read_text()
    assert 'Promoted from **mini**' in body
    assert 'HOUSE RULE: cap requirements at 300.' in body      # the diff is in the PR
    assert 'no retrospective' in out                           # and the rationale nudge

def test_promote_cites_the_retrospective_when_one_exists(project, tmp_path, capsys, monkeypatch):
    seed(); edit()
    os.makedirs('retrospectives', exist_ok=True)
    open('retrospectives/phase-0.md', 'w').write('ceiling is 6')
    argsfile = _fake_gh(tmp_path, monkeypatch)
    origin = _blueprint_repo(tmp_path)
    skills.main(args(promote=[]), cfg={'project': 'mini', 'blueprint_repo': str(origin)})
    assert 'retrospectives/phase-0.md' in argsfile.read_text()

def test_promote_rejects_a_repo_that_is_not_the_blueprint(project, tmp_path, capsys, monkeypatch):
    seed(); edit()
    _fake_gh(tmp_path, monkeypatch)
    bare = tmp_path / 'wrong'
    subprocess.run(['git', 'init', '-q', '--bare', str(bare)], check=True)
    assert skills.main(args(promote=[]), cfg={'blueprint_repo': str(bare)}) == 1
