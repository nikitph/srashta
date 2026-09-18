import os, shutil, pytest
from srashta.common import load_project

FIX = os.path.join(os.path.dirname(__file__), 'fixtures')

@pytest.fixture
def project(tmp_path, monkeypatch):
    """A throwaway copy of the mini project, cwd'd into."""
    d = tmp_path / 'mini'
    (d / 'spec').mkdir(parents=True)
    (d / 'config').mkdir()
    (d / 'build' / 'tickets').mkdir(parents=True)
    (d / '.git').mkdir()          # a real project always has one; status checks for it
    shutil.copy(f'{FIX}/mini-prd.txt', d / 'spec' / 'mini-prd.txt')
    shutil.copy(f'{FIX}/project.yaml', d / 'project.yaml')
    shutil.copy(f'{FIX}/defaults.yaml', d / 'config' / 'defaults.yaml')
    shutil.copy(f'{FIX}/constitution.md', d / 'constitution.md')
    monkeypatch.chdir(d)
    return d

@pytest.fixture
def cfg(project):
    return load_project('project.yaml')
