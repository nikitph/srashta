---
name: spec-authoring
description: Write or repair this project's PRD so it decomposes without repair — stable ids, EARS acceptance criteria, a transition table per stateful object, ADR-form decisions, a total phase plan.
---
# Spec Authoring
Detail: `docs/spec-rules.md` and `templates/spec-skeleton.md` in this repo. Standards: ISO/IEC/IEEE 29148, EARS (Mavin 2009), ADR (Nygard), requirements smells (Femmer 2016).

Your job is the judgment the CLI cannot hold. Gate: `srashta lint`.

**Non-negotiable structure** — stable permanent ids (`FR-DOMAIN-NNN`, withdrawn never renumbered); an id on *every* buildable item including communication-matrix rows; a transition table per stateful object, headed by "any transition not listed is forbidden and must be rejected by the action, not hidden in the interface"; a phase plan naming **every** functional domain; open questions with an owner and what they block; working assumptions as placeholder values.

**Requirement form** — one implementation-free sentence, then EARS criteria (`WHEN` / `WHILE` / `IF…THEN` / `WHERE` / `THE SYSTEM SHALL`), one criterion per test, then free prose rationale. Only those five patterns.

**Enumerate stateful objects deliberately**, including the unglamorous ones — accounts, messages, requests, links. Specs routinely cover headline objects and miss foundations, and four agents then infer four different lifecycles.

**Two failure modes.** A requirement that becomes pseudo-code means you wrote the program twice. And EARS makes a spec consistent and testable, never *correct* — keep the prose good enough that the humans who can spot a wrong requirement will read it.

Repairing an existing spec: same gates as an audit. Report defects against the spec's own ids, ordered by downstream damage — orphaned domains first, missing transition tables second, unidentified items third, smells last. Propose the minimal edit; never rewrite a spec that is already good.
