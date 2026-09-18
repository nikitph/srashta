# Spec rules — the short version

Full guidance in `templates/spec-skeleton.md`. These are the properties the pipeline depends on.

## Non-negotiable
1. **Stable permanent identifiers** (`FR-DOMAIN-NNN`). Withdrawn, never renumbered. Nothing works
   without them: no coverage check, no context pack, no traceability.
2. **Every buildable item has one** — communication-matrix rows included. A row without an ID
   cannot be cited by a ticket or seen by a coverage check.
3. **A transition table per stateful object**, headed by the forbidden-transition rule. Include the
   unglamorous objects: accounts, messages, requests, links.
4. **The phase plan names every functional domain.** `assign.py` refuses to run otherwise.
5. **Open questions carry an owner and what they block.**
6. **Working assumptions carry placeholder values**, so nothing downstream stalls.

## Strongly preferred
7. **Acceptance criteria in EARS**, one criterion per test. Without them, tickets infer their tests
   from prose.
8. **Precise modal verbs** — `must` binds, `should` is tradeable, `may` is an option.
9. **Decisions in ADR form with the rejected alternative**, which is what stops an agent
   re-litigating a settled question.
10. **Explicit non-goals**, which bound what an agent explores.

## Two failure modes
**Over-specification.** A requirement that becomes pseudo-code means the program is written twice,
and the spec now constrains the implementation rather than the outcome.

**False completeness.** Matching a wrong spec satisfies nothing. EARS makes a spec consistent and
testable, never correct. Keep the prose good enough that the humans who can spot a wrong
requirement will actually read it.
