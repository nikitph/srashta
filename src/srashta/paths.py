"""Decidable path-glob intersection and containment, with concrete witnesses.

Grammar: repository-relative POSIX paths, *, ?, ** and **/. Bracket classes and
escapes are rejected rather than guessed. Automata operate on paths that contain
no empty, '.' or '..' segments. No filesystem enumeration: future files count.
"""
from collections import defaultdict, deque
from functools import lru_cache


def validate_pattern(pattern):
    if (not isinstance(pattern, str) or not pattern or pattern.startswith('/')
            or any(c in pattern for c in '[]\\\x00\n\r')
            or any(p in ('', '.', '..') for p in pattern.split('/'))):
        raise ValueError(f'invalid ownership pattern: {pattern!r}; use relative paths with *, ? or **')


class Automaton:
    def __init__(self, pattern):
        validate_pattern(pattern)
        self.edges = defaultdict(list)
        self.literals = set()
        current, count, i = 0, 1, 0
        while i < len(pattern):
            nxt = count
            count += 1
            if pattern[i:i+3] == '**/':
                mid = count
                count += 1
                self.edges[current] += [(None, nxt), ('nonsep', mid)]
                self.edges[mid] += [('nonsep', mid), (('lit', '/'), current)]
                self.literals.add('/')
                i += 3
            elif pattern[i:i+2] == '**':
                self.edges[current] += [(None, nxt), ('any', current)]
                i += 2
            elif pattern[i] == '*':
                self.edges[current] += [(None, nxt), ('nonsep', current)]
                i += 1
            elif pattern[i] == '?':
                self.edges[current].append(('nonsep', nxt))
                i += 1
            else:
                c = pattern[i]
                self.edges[current].append((('lit', c), nxt))
                self.literals.add(c)
                i += 1
            current = nxt
        self.final = current
        self.start = self.closure({0})

    def closure(self, states):
        found = set(states)
        todo = list(states)
        while todo:
            for label, target in self.edges[todo.pop()]:
                if label is None and target not in found:
                    found.add(target)
                    todo.append(target)
        return frozenset(found)

    def step(self, states, char):
        return self.closure({target for s in states for label, target in self.edges[s]
                             if label == 'any' or label == ('lit', char)
                             or (label == 'nonsep' and char != '/')})


@lru_cache(maxsize=2048)
def _compile(pattern):
    return Automaton(pattern)


def matches(pattern, path):
    if not path or any(p in ('', '.', '..') for p in path.split('/')):
        return False
    a = _compile(pattern)
    states = a.start
    for char in path:
        states = a.step(states, char)
    return a.final in states


def _witness(pattern, others, difference):
    machines = [_compile(pattern)] + [_compile(p) for p in others]
    chars = set('/.') | set.union(*(m.literals for m in machines))
    other = 'x'
    while other in chars:
        other = chr(ord(other) + 1)
    chars.add(other)
    initial = (tuple(m.start for m in machines), 0)
    todo, seen = deque([(initial, '')]), {initial}
    while todo:
        (states, segment), prefix = todo.popleft()
        accepts = [m.final in s for m, s in zip(machines, states)]
        if segment == 3 and accepts[0] and (not any(accepts[1:]) if difference else all(accepts[1:])):
            return prefix
        for char in sorted(chars):
            if char == '/':
                if segment != 3:
                    continue
                seg = 0
            else:
                seg = (segment + 1 if segment in (0, 1) else 3) if char == '.' else 3
            nxt = tuple(m.step(s, char) for m, s in zip(machines, states))
            if not nxt[0] or (not difference and any(not x for x in nxt[1:])):
                continue
            key = (nxt, seg)
            if key not in seen:
                seen.add(key)
                todo.append((key, prefix + char))
    return None


@lru_cache(maxsize=4096)
def intersect(a, b):
    validate_pattern(a); validate_pattern(b)
    if not any(c in a + b for c in '*?'):
        return a if a == b else None
    if not any(c in a for c in '*?'):
        return a if matches(b, a) else None
    if not any(c in b for c in '*?'):
        return b if matches(a, b) else None
    return _witness(a, (b,), False)


def outside(pattern, allowed):
    """Return a path owned by pattern but not by the union of allowed patterns."""
    return _witness(pattern, tuple(allowed), True)
