from srashta.gentests import generate

M = {'account': {'states': ['active', 'suspended', 'gone'], 'terminal': ['gone'],
                 'transitions': [{'from': 'active', 'to': 'suspended'},
                                 {'from': 'suspended', 'to': 'active'},
                                 {'from': 'active', 'to': 'gone'}]}}

def test_permitted_and_sneak_path_counts(tmp_path):
    _, c = generate(M, 'pest', str(tmp_path))
    permitted, forbidden = c['account']
    assert permitted == 3
    # 3 states -> 9 ordered pairs (including self), minus 3 listed = 6
    assert forbidden == 6

def test_terminal_state_has_no_exit_at_all(tmp_path):
    generate(M, 'pest', str(tmp_path))
    body = (tmp_path / 'accountTest.php').read_text()
    assert '["gone", "active"]' in body and '["gone", "gone"]' in body

def test_every_flavour_renders(tmp_path):
    for f in ('pest', 'pytest', 'vitest'):
        w, _ = generate(M, f, str(tmp_path / f))
        assert len(w) == 1 and (tmp_path / f).exists()
