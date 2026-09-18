# What the coding master agent needs

Not just tickets. Seven things — and one it must **not** have.

## 1. A scaffolded repository, with contracts already merged

The orchestrator does not start from an empty directory. Before any feature ticket runs, the repo
holds: the stack scaffold, `constitution.md`, the phase's contracts built and green (schema,
state machines, action stubs, event schemas, interfaces with fakes), the design system frozen
(tokens, patterns, `DESIGN.md`), and CI wired.

A feature agent that arrives to an empty repo invents the contract. That is the failure this whole
method exists to prevent, so the contract wave is not optional and is not parallelisable with the
work that depends on it.

## 2. The ticket graph — `build/tickets/phase-N.json`

Conforms to `schemas/ticket.schema.json`. This is the routing and eligibility interface:
`depends_on`, `wave`, `blocked_on`, `owned_files`, `kind`.

Eligibility: `blocked_on` empty, every dependency merged, lowest wave with unfinished work.
Tickets within a wave own disjoint files and run concurrently.

## 3. One context pack per ticket — and nothing else

`build/context-packs/phase-N/<ID>.md`, ~1,000 tokens, plain Markdown. The sub-agent gets this and
no more. It carries the constitution, the full text of its requirements, the domain rules it needs,
the contracts it may use, its exclusive file paths, the config keys to read, its acceptance tests,
and the evidence to attach.

## 4. Runtime configuration — `config/defaults.yaml`

Agents read parameters, never hardcode them. A key still marked `status: blocker` throws outside an
acknowledged non-production context, which is what stops a provisional value shipping.

## 5. Generated tests, already in the repo

Transition tests (`pipeline/gen_transition_tests.py`) and consumer contract tests for events. These
are part of CI before any feature ticket runs, so an agent that breaks a state machine or drifts an
event payload fails immediately rather than at integration.

## 6. CI that enforces the constitution

The prose rules an agent can quietly drop need to be checks: semantic-token lint (no raw hex, no
palette utilities, no arbitrary values), accessibility, dependency scan, and the generated tests
above. A rule that is only written down is a suggestion.

## 7. Conventions — branch, PR, evidence, escalation

- Branch per ticket id; fresh workspace.
- Acceptance tests written as failing tests first, then implementation.
- PR carries the ticket's listed evidence.
- Human review for `C-` and `I-` tickets; feature tickets auto-merge on green **unless** they
  touched a file outside their owned set.
- **An agent needing a frozen contract changed stops and files a contract-change ticket.** It does
  not edit and continue — that silently unfreezes a design rule every concurrent ticket relies on.
- A pack with a BLOCKED banner is not started.

## And the write-back: telemetry

Per ticket: `attempts`, `first_run_test_failures`, `contract_change_filed`,
`out_of_scope_files_touched`, `review_rounds`, `agent`, `diff_lines`.

This is the only thing the orchestrator owes back, and it is what makes step 7 measurement rather
than opinion — including the open question of correct ticket size.

---

## What it must NOT have

**The specification.** An agent handed the whole spec drifts toward whatever else is in it. The
packs exist precisely so no executing agent ever reads the PRD.

**Write access to frozen contracts.** Enforced by review, not just by instruction.

**Network access during tests.** Every external dependency has an in-memory fake. A test that
reaches the network is flaky and slow, and hides a missing interface.

---

## Routing across models

Route by ticket `kind`, not by preference. Contract and integration tickets carry the most
consequence — a contract error propagates to every ticket in the phase, and an integration failure
is the phase gate. Give those to the strongest available model. The widest wave is independent and
well-specified, so fan it out.

Update routing from `retrospectives/phase-N.md`, never from impressions.
