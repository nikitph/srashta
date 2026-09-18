# <Product> — Product Requirements Document

Version 0.1 · Draft · <date> · Owner: <name>

> Delete this block before circulating.
> Conformance is checked by `pipeline/lint_spec.py`. Rationale and context stay in prose —
> the spec has human readers whose job is to notice a *wrong* requirement, which no linter does.
> Only acceptance criteria are constrained.

## Requirement conventions

Identifiers are `FR-DOMAIN-NNN` and `NFR-NNN`, and are **permanent**: a dropped requirement is
marked withdrawn, never renumbered, so review comments and test cases stay anchored.

| Priority | Meaning | Test for inclusion |
|---|---|---|
| P0 | Minimum viable | <what cannot happen without it> |
| P1 | Fast follow | <felt as friction, not failure> |
| P2 | Later | <listed so the data model does not foreclose it> |

`must` binds. `should` is a strong default, tradeable with a recorded rationale. `may` is an
option retained for later.

## Part I — Context
1. Problem statement · 2. Actors and personas · 3. Primary journeys (J1…Jn) · 4. Success metrics

## Part II — Scope
5. In scope by actor · 6. **Explicitly deferred** · 7. Dependencies and external assumptions

## Part III — Functional requirements
One section per domain. Domains become modules, so draw them where you want module boundaries.

```
FR-XXX-001 [P0]
<One sentence. Singular. Implementation-free.>

Acceptance criteria
  WHEN <trigger> THE SYSTEM SHALL <response>.
  IF <unwanted condition> THEN THE SYSTEM SHALL <handling>.
  WHILE <state> THE SYSTEM SHALL <invariant>.
  WHERE <feature present> THE SYSTEM SHALL <behaviour>.
  THE SYSTEM SHALL <ubiquitous invariant>.

Rationale
  <free prose, optional>
```

Use only those five EARS patterns. One criterion = one test. If a criterion needs two tests, it
is two criteria.

## Part IV — Non-functional requirements
Performance · availability and resilience · security · data protection · accessibility and
internationalisation · observability and operations. Each `NFR-NNN`, each verifiable.

## Part V — Decisions and questions

**Design decisions**, in ADR form:
```
Decision: <what was decided>
Context: <what forced a choice>
Consequences: <what follows, including what becomes harder>
Rejected: <the alternative, and why it lost>
```
The rejected alternative is what stops an agent re-litigating a settled question.

**Working assumptions**: every parameter the design needed, with a placeholder value and why it
matters to the build. Placeholders become config defaults, so nothing downstream stalls.

**Open questions register**: one numbered list, each with an owner and **what it blocks**.
Retain answered questions with their decision rather than deleting them.

## Part VI — Delivery
Phases defined by **verifiable exit gates**, not dates. **Every functional domain must be named
in exactly one phase.** A domain named in none is orphaned by any phase-driven decomposition; a
phase whose gate needs a capability assigned later cannot meet its own gate.

## Appendices
- **A Glossary** — every term used precisely.
- **B State machines** — one transition table per stateful object. Head the appendix with:
  *permitted transitions only; any transition not listed is forbidden and must be rejected by the
  application action, not merely hidden in the interface.* Include the unglamorous objects:
  accounts, messages, requests, links.
- **C Communication matrix** — every message, **each row carrying an ID** (`MSG-NNN`). A row
  without an identifier cannot be cited by a ticket or seen by a coverage check.
- **D Role capability summary**
- **E Requirement summary** — prefix → domain → section.
