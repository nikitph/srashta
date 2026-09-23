# Srashta: structural specification process

Date: 23 September 2026. Revision 2. Status: process addendum, with a worked planning review. Revision 2 adds review amendments A1–A6 (listed at the end). These rules are not yet implemented in the Python compiler. No application behavior, domain approval or exhaustive specification coverage is certified here.

Source: [user-supplied structural rules](references/structural-rules.md). Rule identifiers below refer to that document. [Aarogya application](AAROGYA.md) shows the practical change to our existing trial.

## What changes

The target remains an executable ticket graph for our fixed Laravel foundation. Insert a structured behavior contract between product discovery and ticket recipes:

`idea + foundation profile → use cases → behavior contracts → recipe bindings → ticket DAG + acceptance plan`

These are progressively refined records, not five disconnected documents. Interview answers fill missing records. The prose specification, register tables, worker briefs and graph are views of the same versioned model.

The foundation fixes implementation mechanisms. The product specifies their meaning: a queue supplies execution infrastructure, but does not decide how long a hospital should wait, what a failed delivery means, or who can override a billing guard.

## Progressive workflow

1. **Load the foundation profile.** Pin its revision and distinguish available library affordances, configured capabilities and behavior verified at an exact revision. Reuse applicable guarantees and test recipes. A latent capability creates activation/configuration work when selected; it does not count as already delivered.
2. **Describe one use case.** Identify actor, desired outcome, authoritative inputs, writer ownership and observable completion. Keep synchronous reads explicit. Discover related modules without specifying their entire interiors.
3. **Expand its behavioral obligations.** Record invariants, states, transitions, authority, time, races, policy snapshots and boundary failures. Instantiate only applicable register types. Every omission needs an applicability reason; a blank field is not a decision. For P0 records, an omission is valid only under the origin rule in A1.
4. **Resolve the necessary product decisions.** Ask questions whose answers change outcomes or contracts. Use the foundation for already fixed architecture. Preserve unknown answers as decision records with owner, affected records, and the stage they block.
5. **Bind to recipes.** Each obligation gets an implementation owner, an enforcement mechanism and acceptance evidence. One ticket may own several related obligations. Do not create a ticket for each register row.
6. **Compile prerequisites.** Contract work precedes implementations that consume it. Real integration verification depends on all required providers and consumers. Separate implementation prerequisites, evidence prerequisites and decision gates from descriptive relationships.
7. **Review readiness per dependency closure.** A diagnostic graph may contain open decisions. An implementation-ready ticket may not leave its behavior or required contracts undecided. Verification-ready requires real bindings and approved outcome examples where applicable. Completion requires executed evidence, not a test plan.

## The model to maintain

Use the source's ten register views: ownership, invariants, state machines, timers, parameters, authority, external boundaries, messages, concurrency and worked examples. Add an **operation record** so transaction and saga rules have an explicit home:

`operation_id, orchestrator, participating owners, authoritative reads, steps, commit boundaries, observable completion, failure guarantees, external effects, recovery, decision_refs`

Generate schema obligations, retention relationships, contradictions and acceptance plans as linked views. Avoid duplicate prose as a second source of truth.

Every semantic record carries:

- Stable namespaced ID and source requirement/criterion references.
- Origin: explicit source, inherited foundation, proposed interpretation or approved decision.
- Owner, applicability and priority.
- Contract and capability references, including version and evidence where inherited.
- Open decisions and their blocking stage.
- Implementing ticket and acceptance-plan references once bound.

Use separate fields for semantic approval and implementation evidence. An inherited obligation still exists. Its reusable evidence is conditional on the same version, configuration and usage assumptions. Product-specific use still needs integration checks.

### Decision records (A4)

Decision records are versioned, not overwritten:

`decision_id, question, answer, owner, origin, effective_from, supersedes, superseded_by, affected_records, blocking_stage, rationale`

A superseded decision is treated as a semantic change to every record in `affected_records`: those records, their bound tickets and their acceptance cases return to review under V6. A record whose decision reference points at a superseded decision cannot hold `semantics_reviewed`.

### Inherited evidence invalidation (A3)

Inherited evidence records the foundation revision, configuration and usage assumptions it was verified under. When the pinned foundation revision changes, every record whose evidence was inherited from a changed capability drops from `behavior_verified` to `semantics_reviewed` until its evidence is re-established at the new revision. Unchanged capabilities keep their evidence. The foundation profile must therefore state, per capability, which revision last changed it.

## Rule adoption and amendments

“Adopt” retains the obligation, not the source's claim that all checks are mechanical. The amendments below take precedence in our process.

| Source rules | Treatment in Srashta |
|---|---|
| R1–R2 | Adopt single write ownership and named orchestration. Ownership of data is distinct from ownership of a transaction. |
| R3 | Adopt source/derivation/drift handling for replicas and projections. Distinguish immutable historical snapshots from replicas expected to track current state. |
| R4 | Use wording as an extraction heuristic. It neither proves completeness nor establishes the correct interpretation. |
| R5 | Require explicit enforcement, usually layered across types, database and actions. There is no universal strength ordering. Database-enforceable critical constraints need a concrete mapping or a reviewed technical exception and alternative. |
| R6–R10 | Adopt state obligations and complete handling of the declared event vocabulary. Duplicate events may be acknowledged idempotently rather than rejected. Terminal means no lifecycle exit; it does not prohibit reads or retry acknowledgments. |
| R11–R15 | Require bounded recovery for states with a promised progression. A stable active account or indefinitely editable draft need not expire. Every non-terminal state carries an explicit `progression` classification (`promised` or `none`); for P0 states, `none` requires an approved decision (A1). Record overdue grace, scheduler cadence and escalation. Zero overdue rows is a drained-fixture assertion, not an unconditional production guarantee. Enforce hard expiry at the action/read boundary where required. |
| R16 | Adopt explicit time, catch-up, idempotency and scheduler health. Define time zone and exact boundary inclusivity for relevant rules. |
| R17–R18 | Use the actual commit boundary. Several modules can participate in one shared database transaction via their own actions. Independent commits require an explicit recovery protocol; choose a saga when the business operation requires coordinated compensation or forward recovery. A notification alone need not create a saga. Never claim a remote effect rolls back with local state. |
| R19 | Classify historical facts, current-status assertions and requests. Declare supersession behavior per message. A committed historical fact can remain valid after later transitions; do not universally drop it. A timed-out request may expire or escalate without a compensating mutation. |
| R20–R21 | Adopt authentication, deduplication, ordering, late/lost-event and reconciliation obligations. Include humans as dependencies where their absence can stall promised progress; not every role requires a provider-style callback contract. Close each provider's declared event vocabulary against the provider's published event catalogue at a pinned catalogue version (A2). |
| R22 | Propagate required priority to the necessary capability slice, not its entire module or optional neighboring features. The slice is defined mechanically as the closure of operation records, contracts, timers and boundary records reachable from the prioritised record through typed references (A5). |
| R23 | Name the evidence supporting an assertion. An authoritative verified acknowledgment can be sufficient; periodic reconciliation is required where loss or divergence can invalidate confidence. |
| R24–R25 | Extract changeable policy values with authority, effective dates and decision snapshots. Numbers in worked examples, structural cardinalities and measurable acceptance targets are permitted in prose. Distinguish approved values from placeholders. |
| R26 | Keep versioned code for behavior and tables for policy values as our house default. Treat a data-driven workflow engine as an explicit architectural departure, not an impossible design. |
| R27–R30 | Adopt authority scope, recorded overrides and race outcomes. Define eligible overrides; structural/security invariants are not implicitly waivable. State the allowed concurrent outcomes, which may include multiple successes or an idempotent replay. A P0 operation classified as non-exclusive (no race obligation) requires an approved decision (A1). |
| R31–R32 | Adopt constraint mapping and retention-safe references. Test against the chosen database and application role. Application observers alone are not proof that bypass writes are prevented. |
| R33 | Adopt domain-reviewed calculation examples before accepting financial correctness. Unsigned examples remain proposals. Examples supplement properties and review; one example does not prove a formula correct. |
| R34 | Adopt explicit contradiction findings with both source references and a decision owner. An empty finding list means none found in the reviewed scope, not a proof of consistency. |

The transaction distinction follows the database's actual all-or-nothing boundary; our mapping of that boundary to modules is an architectural choice. See [PostgreSQL transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html). An outbox records the event with the business commit and publishes afterwards, but can still deliver duplicates; see [AWS transactional outbox guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html).

### Applicability and the origin rule (A1)

Applicability reasons are necessary, and they are also the easiest way for a planner under pressure to reach a clean plan by classifying hard cases away. The following classifications therefore require origin `approved decision` when the affected record is P0, and may not rest on `proposed interpretation`:

- a register type or register row marked `not_applicable`;
- a non-terminal state classified `progression: none`;
- an operation classified as non-exclusive, removing its race obligation;
- a provider event marked `ignored`;
- an invariant classified as waivable by override.

A planner or worker may propose any of these. It may not grant them to itself. Until approved, the classification is an open decision that blocks `implementation-ready` for the affected dependency closure. For non-P0 records, `proposed interpretation` is permitted but is reported in the readiness review.

## Acceptance and test derivation

Adopt acceptance-first plans and bidirectional traceability (V3, V5). Derive the expected outcomes from approved contracts rather than copying observed implementation behavior.

| Source rules | Treatment |
|---|---|
| V1 | Protect the acceptance oracle through review and change control. Implementers can read acceptance tests and write unit tests. Reviewing implementation for integration setup is permitted; it must not silently redefine the expected behavior. No mandatory multi-agent workflow. |
| V2 | Use risk-based mutation and fault injection. Triage surviving mutants as behavioral gaps, equivalent mutations, invalid mutations or exclusions with reasons. Do not delete a valuable test merely because a mutant survived. Runtime mutation evidence is collected after executable code exists. |
| V4 | Keep model/contract tests reproducible through injected time, seeded generation and provider fakes. Maintain separate real database, concurrency, provider and performance suites with their environmental limitations recorded. |
| V6 | Review affected tests on semantic changes, including superseded decisions (A4) and foundation revisions affecting inherited evidence (A3). Test corrections or harness refactoring can preserve the contract; record their rationale rather than inventing a requirement change. |
| T1–T2 | Derive transition, actor, guard and stateful-property checks. Assert invariants at declared observable boundaries. Guard failure behavior follows the declared failure guarantee; security logs or attempt counters may still be written. |
| T3 | Derive before/at/after-deadline, missed-run, duplicate-run and backstop cases. Assert the defined processing/grace bound rather than instantaneous production emptiness. |
| T4 | Test permitted race histories and invariant preservation. “Exactly one winner” applies only to exclusive operations; repeated identical requests can return the same success. |
| T5–T6 | Inject duplicate, reordered, late, lost and invalid events. Test the specified message supersession policy. Model an ambiguous provider outcome explicitly; local idempotency cannot promise no duplicate remote delivery. |
| T7–T10 | Adopt enforcement-layer probes, historical policy tests, authority/aggregation tests and exact approved calculation oracles. Assert limits' specified inclusive/exclusive boundaries, not an assumed convention. |

For outbox mutation tests, the defect is **publishing before commit or persisting outside the business transaction**. Merely inserting the outbox row earlier inside the same atomic transaction is not necessarily a defect.

Retain C1–C39 as a source checklist and map them to these amended obligations. A future checker must distinguish `pass`, `fail`, `open`, `not_applicable_with_reason` and `not_evaluated`. This addendum does not claim to have executed all 39 checks.

## What the compiler can and cannot prove

Mechanically check IDs, references, single declared ownership, complete declared state/event matrices, required fields, timer coverage classifications, typed prerequisite binding, cycles, priority propagation, decision propagation, and acceptance-plan references. Such checks operate over the inventory supplied to them.

### Inventory closure checks (A2)

Inventory completeness cannot be proved in general, but parts of it can be closed against sets the compiler can see. These are mechanical checks:

- **Provider catalogue closure.** For each external boundary, the declared event vocabulary equals the provider's published event catalogue at a pinned catalogue version. Every catalogue event appears in at least one state machine's coverage matrix or carries an `ignored` classification subject to A1.
- **Coupled-machine closure.** For every declared coupling, every state of the driving machine appears in the mapping table.
- **Example closure.** Every entity, state, event and parameter named in an approved worked example exists in the inventory.
- **Decision closure.** Every record referenced by a decision's `affected_records` exists, and every decision reference on a record resolves to a non-superseded decision or is flagged.
- **Classification closure.** Every non-terminal state has a `progression` classification; every operation has an exclusivity classification; every P0 classification that removes an obligation satisfies A1.

These reduce, but do not replace, semantic review.

Semantic review must establish whether that inventory is complete, the invariants describe the intended business behavior, actors are correctly distinguished, a constraint actually enforces the claim, and the worked answers are right. A field containing text is not proof of any of those things.

Actual enforcement, concurrency behavior, scheduler recovery and provider guarantees require executable evidence. Keep `plan_valid`, `semantics_reviewed` and `behavior_verified` separate.

## How this changes the ticket graph

Maintain two different graphs:

- The **domain relationship graph** may contain cycles: users request approval, approval affects users; billing initiates delivery, delivery updates billing metadata.
- The **implementation prerequisite graph** must be a DAG. Publish shared contracts before participants and join their real implementations at integration verification. Do not translate every domain relationship into an implementation prerequisite.

For example, a shared invariant across billing, deposits and ledger yields one operation contract, distinct owner implementations and a verification join. It does not require merging all modules or making each participant depend on every other participant's implementation.

Ticket briefs gain references to applicable transitions, invariants, failures, timers, races and acceptance cases. The foundation provides the mechanism once; recipes instantiate the obligations and integration checks on each use. Only an unsatisfied obligation creates additional work.

If a newly exposed relationship produces an implementation cycle, investigate contract placement, ownership or an incorrectly typed edge. Do not remove a real prerequisite simply to obtain a DAG.

## Next implementation increment

First extend one existing use case's authored inputs with the records above, bind its records to the existing tickets and emit the richer briefs and acceptance plan. Then implement structural checks with negative fixtures for:

- a missing owner;
- an uncovered late event;
- an absent deadline mechanism;
- an unbound real provider;
- an unpropagated decision;
- a P0 `not_applicable` or `progression: none` classification with origin `proposed interpretation` (A1);
- a provider catalogue event absent from every coverage matrix (A2);
- inherited evidence still marked verified after its capability changed in a foundation revision bump (A3);
- a record referencing a superseded decision while marked `semantics_reviewed` (A4).

Run the old and new planners on the same scope and foundation assumptions.

### Measuring invented behavior (A6)

"Whether an implementer had to invent behavior" must be counted, not judged after the fact. Require every implementer to emit an `invented_decision` record for each choice the brief, contracts and acceptance plan did not determine:

`invented_decision_id, ticket_id, question, choice_made, alternatives_considered, affected_behavior, severity (cosmetic / behavioral / contractual), suggested_record`

Compare, between the old and new planner runs: the count of invented decisions, their severity distribution, and how many correspond to a missing or `open` record in the model. Each behavioral or contractual invented decision is a finding against the model, and its `suggested_record` is the candidate fix.

Also compare unresolved worker choices, missing/redundant prerequisites, criterion coverage and repair effort. Ticket count and fewer edges alone are not quality measures. Preserve the original trial as the comparison baseline.

## Revision 2 amendments

| ID | Amendment | Sections affected |
|---|---|---|
| A1 | Obligation-removing classifications on P0 records require an approved decision; planners may propose but not grant them. | Workflow step 3; R11–R15; R27–R30; Applicability and the origin rule |
| A2 | Mechanical inventory closure against provider catalogues, coupled machines, worked examples, decisions and classifications. | R20–R21; Inventory closure checks |
| A3 | Foundation revision changes invalidate inherited evidence for changed capabilities. | Inherited evidence invalidation; V6 |
| A4 | Decision records are versioned with supersession, and supersession propagates review. | Decision records; V6 |
| A5 | Priority slice defined as the typed-reference closure from the prioritised record. | R22 |
| A6 | Invented behavior measured through `invented_decision` records emitted by implementers. | Measuring invented behavior |