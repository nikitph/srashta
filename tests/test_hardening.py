"""Regression tests for guarantees crossing CLI, Git and artifact boundaries."""
import copy
import json
from pathlib import Path

import pytest

from srashta import extract, validate, waves


def test_markdown_format_parses_its_own_priority_and_criteria(cfg):
    Path(cfg['spec']['path']).write_text('''# Specification
```
FR-ACC-001 [P0]
Registration must be atomic.

Acceptance criteria
  WHEN a person registers
  THE SYSTEM SHALL create an account.

Rationale
  Do not duplicate accounts.
```
''')
    rows = extract.main(cfg)
    assert rows[0]['priority'] == 'P0'
    assert rows[0]['criteria'] == ['WHEN a person registers THE SYSTEM SHALL create an account.']
    assert 'Registration must be atomic.' in rows[0]['text']
    assert 'Rationale' not in rows[0]['text']


@pytest.mark.parametrize('a,b', [
    ('app/Models/*User.php', 'app/Models/Admin*.php'),
    ('app/**/User?.php', 'app/Models/*1.php'),
    ('app/**', 'app/*/User.php'),
])
def test_intersection_returns_an_actual_path(a, b):
    from srashta.paths import matches
    witness = validate.globs_intersect(a, b)
    assert witness and '*' not in witness and '?' not in witness
    assert matches(a, witness) and matches(b, witness)


def test_ownership_requires_subset_not_just_overlap():
    from srashta.paths import outside
    assert outside('app/**', ['app/Models/**'])
    assert outside('app/Models/*.php', ['app/**']) is None


def test_duplicate_ticket_ids_are_not_silently_collapsed():
    t = dict(id='C-01', title='Contract', module='identity', depends_on=[],
             owned_files=['app/c.php'], requirements=[], acceptance_tests=['check'], evidence=['log'])
    with pytest.raises(SystemExit, match='duplicate'):
        waves.finalise([t, copy.deepcopy(t)])


def test_approval_binds_the_exact_design(cfg):
    from srashta import approvals
    Path('contracts').mkdir()
    Path('contracts/phase-0.md').write_text('first design')
    approvals.approve(cfg, 0, 'operator')
    assert validate.approval_marker(cfg, 0) is None
    Path('contracts/phase-0.md').write_text('different design')
    assert 'changed' in validate.approval_marker(cfg, 0)


def test_empty_approval_marker_is_not_approval(cfg):
    Path('contracts').mkdir()
    Path('contracts/phase-0.md').write_text('design')
    Path('contracts/phase-0.approved').touch()
    assert validate.approval_marker(cfg, 0)


def test_nonterminal_self_transitions_are_tested(tmp_path):
    from srashta.gentests import generate
    _, counts = generate({'item': {'states': ['open', 'closed'], 'terminal': ['closed'],
                                'transitions': [{'from': 'open', 'to': 'closed'}]}},
                         'pytest', str(tmp_path))
    assert counts['item'] == (1, 3)


def test_unknown_dependencies_report_defect_instead_of_crashing():
    with pytest.raises(SystemExit, match='unknown'):
        waves.finalise([dict(id='T-01', title='Ticket', module='identity',
                            depends_on=['C-99'], owned_files=['app/a.php'], requirements=[],
                            acceptance_tests=['check'], evidence=['log'])])


def test_indented_reference_in_rationale_is_not_a_duplicate(cfg):
    Path(cfg['spec']['path']).write_text('FR-ACC-001 [P0] First\nRationale\n  FR-ACC-001 requires this behavior.\n')
    assert len(extract.main(cfg)) == 1
