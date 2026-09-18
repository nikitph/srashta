import json, pytest, yaml
from srashta import extract, assign

def test_parses_every_identifier(cfg, capsys):
    reqs = extract.main(cfg)
    ids = {r['id'] for r in reqs}
    assert len(reqs) == 12
    assert 'FR-ACC-001' in ids and 'NFR-002' in ids
    assert all(r['priority'] in ('P0', 'P1', 'P2') for r in reqs)

def test_multiline_text_is_joined(cfg):
    reqs = {r['id']: r for r in extract.main(cfg)}
    assert 'password' in reqs['FR-ACC-001']['text']          # wrapped across two lines
    assert 'invalidate all existing sessions' in reqs['FR-ACC-003']['text']

def test_ears_criteria_are_not_swallowed_as_new_rows(cfg):
    reqs = {r['id']: r for r in extract.main(cfg)}
    assert any('THE SYSTEM SHALL create an account' in c for c in reqs['FR-ACC-001']['criteria'])

def test_refuses_a_partial_parse(cfg):
    """A too-narrow id pattern must fail loudly, never silently drop a domain."""
    cfg['spec']['id_pattern'] = r'FR-ACC-\d{3}'
    with pytest.raises(SystemExit) as e:
        extract.main(cfg)
    assert 'id_pattern does not match' in str(e.value)
    assert 'FR-BIL' in str(e.value)
