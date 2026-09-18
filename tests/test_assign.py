import pytest
from srashta import extract, assign

def test_every_requirement_gets_one_module_and_one_phase(cfg):
    extract.main(cfg)
    reqs = assign.main(cfg)
    assert len(reqs) == 12
    assert all(r['module'] and r['phase'] is not None for r in reqs)
    assert {r['phase'] for r in reqs} == {0, 1}

def test_refuses_a_domain_named_in_no_phase(cfg):
    """The defect that silently orphans whole sections of a spec."""
    extract.main(cfg)
    cfg['phases'][0]['domains'] = ['ACC', 'NFR']       # NOT dropped
    with pytest.raises(SystemExit) as e:
        assign.main(cfg)
    assert 'named in no phase' in str(e.value)

def test_override_requires_a_reason(cfg):
    extract.main(cfg)
    cfg['overrides'] = {'FR-ACC-004': {'phase': 1}}
    with pytest.raises(SystemExit) as e:
        assign.main(cfg)
    assert 'no reason' in str(e.value)
