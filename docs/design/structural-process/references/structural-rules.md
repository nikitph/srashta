# Spec Structural Rules: Invariants, State, Time and Boundaries

## Purpose

You are reviewing or authoring a product specification (PRD) so that its structural properties are explicit before any code is written. Most serious defects in stateful systems are not errors of judgment. They are missing structure: an unowned invariant, a state with no exit, a time rule nobody fires, an "atomic" claim that spans an email server. This document tells you how to make that structure explicit and how to check it.

Apply these rules:

- **When authoring** a spec: produce the ten registers in Part 3 alongside the prose requirements.
- **When reviewing** a spec: extract the registers from the prose, run the checklist in Part 5, and report every failure.
- **When deriving tests**: generate the test plan from the registers using Part 8, before any implementation code exists.

Do not rewrite the prose requirements unless asked. The registers are the structural contract; the prose explains intent.

---

## Part 1: Core concepts

Use these definitions consistently.

- **Invariant**: a statement about system state that must be true whenever the state is observable from outside its owner. May be temporarily false *inside* an operation, never at its boundary.
- **Owner**: the single module permitted to write a piece of state. Everyone else reads it or asks the owner to change it.
- **Precondition**: what the caller must make true before an operation. Caller's responsibility.
- **Postcondition**: what the operation guarantees afterwards, given the precondition held. Callee's responsibility. Usually relates the new state to the old state.
- **Failure guarantee**: what holds if the operation fails. One of: `no-fail`, `strong` (all-or-nothing), `basic` (invariants hold, state may have changed), `none`.
- **Safety property**: something bad never happens. Violations occur at an identifiable moment. Enforced by prevention.
- **Liveness property**: something good eventually happens. Pure liveness can never be observed to fail; convert it to **bounded liveness** (a deadline) so it can be monitored.
- **Terminal state**: a state with no exits, intentionally.
- **Dead state**: a state with no exits, unintentionally. Always a defect.
- **Stuck state**: a state whose exits all depend on a party outside the system's control, with no timer. A latent dead state.
- **Pivot**: the step in a multi-step operation after which the outcome is final.
- **Assert message**: a message that states an outcome as fact ("your order is cancelled"). May only be sent after the pivot.
- **Request message**: a message that asks for an action the process needs ("verify your email"). May be sent before the pivot if it has a timeout and a compensation.
- **Parameter**: a value decided by an authority that can change without code changing (a limit, a rate, a window).
- **Structure**: something the logic is built around; changing it requires code changes (states, step sequences, formulas).
- **Cross-cutting invariant**: an invariant over state owned by more than one party. Within the system, prefer to eliminate it (merge owners, or derive instead of duplicating). At external boundaries it cannot be eliminated, only verified by reconciliation.

---

## Part 2: The rules

Each rule has a **Check** that can be evaluated mechanically. Cite rule IDs in all findings.

### A. Ownership

**R1. One owner per entity.** Every stateful entity has exactly one owning module. Only that module's actions write it.
*Check:* every entity in the ownership map has exactly one owner; no requirement describes another module writing it directly.

**R2. Cross-module operations have a named orchestrator.** Any operation that changes state in more than one module names one orchestrating action that owns the transaction and invokes each module's own actions.
*Check:* every operation touching two or more modules names its orchestrator.

**R3. No duplicate state without a derivation rule.** If the same fact is stored in two places (cache, projection, mirror, cached balance), name the source of truth, the derivation, and the reconciliation that detects drift.
*Check:* every duplicated fact has all three.

### B. Invariants

**R4. Wording routes to registers.** Scan every requirement sentence. Route by wording:

| Wording in the requirement | Register |
|---|---|
| never, only, must not, at most, exactly one, cannot | Invariant register |
| within, after, before, expires, eventually, until, deadline, window | Timer register |
| atomically, in one outcome, together, all-or-nothing | Atomicity check (R17) |
| notify, send, email, remind, message, alert (to a person) | Message register |
| configurable, policy, limit, threshold, window, rate, percentage, band | Parameter register |
| callback, webhook, provider, external, third-party, sync | Boundary register |
| capacity, hold, reserve, concurrent, double-book, simultaneously | Concurrency register |
| may, authorised, approve, role, permission, on behalf of | Authority matrix |

*Check:* every matching sentence has at least one register entry citing its requirement ID.

**R5. Every invariant names its strongest enforcement.** Preference order: `type` → `db-constraint` → `owning-action` → `reconciliation`. `documented-only` is not permitted for P0 invariants.
*Check:* no P0 invariant is `documented-only`; any invariant expressible as a database constraint is enforced as one.

**R6. Per-state invariants are explicit.** For every state of every state machine, list fields that must be present and fields that must be absent.
*Check:* every state has a per-state invariant entry, even if "none".

### C. State machines

**R7. Every status field has a full transition table** with all of these columns:

`from | to | event | actor | guard (precondition) | effect (postcondition) | concurrency rule | failure guarantee`

*Check:* every entity with a status, state or lifecycle has a table; no column is blank.

**R8. Every (state, event) pair is answered.** Each event is either a listed transition or explicitly rejected, in every state. Mandatory for external events, which can arrive late, duplicated or out of order in any state.
*Check:* for each external event, every state has a transition or an explicit rejection with defined behavior.

**R9. Triggers name the actor precisely.** "When the tutor joins", never "when a participant joins". Ambiguous actors create transitions that fire for the wrong reason and block the transitions that should fire.
*Check:* no trigger uses a generic actor where the role matters.

**R10. Terminal states are declared.** Every state with no outgoing transitions appears in a terminal list with a reason.
*Check:* exitless states = declared terminal states.

**R11. No state depends solely on an uncontrolled party to exit.** If every exit requires action by a human or external system, the state must also have a timer transition (see R13).
*Check:* every non-terminal state has at least one exit the system itself can fire.

**R12. Coupled machines have a mapping table.** When one entity's state implies another's (e.g. order → enrolment → earning), give the explicit pairing for every state of the driving machine.
*Check:* every coupled pair has a complete mapping; no driving state is unmapped.

### D. Liveness and time

**R13. Every waiting state is in the timer register** with a driver (what makes it move), a bound (how long it may wait), and a fallback (what happens when the driver does not act).
*Check:* every non-terminal state appears in the timer register or is justified as not waiting.

**R14. Deadlines are stored as data.** A waiting state records its deadline when entered (`expires_at`, `respond_by`, `release_after`). The spec includes a monitoring query: objects past deadline still in the waiting state. This query must always return zero rows.
*Check:* every timer register entry names its deadline field and monitoring query.

**R15. No time condition depends solely on an event that might never occur.** Conditions such as "until the second session" or "once approval arrives" require a calendar backstop.
*Check:* every event-conditioned timer has a backstop date or duration.

**R16. Time is an explicit input.** Domain logic receives an as-of time and never reads the clock directly. Scheduled jobs process everything due up to now (catch-up, never "due today only"), are idempotent, and have a last-successful-run alert.
*Check:* every scheduled job states its catch-up query, idempotency mechanism and heartbeat.

### E. Atomicity and external effects

**R17. Atomicity is claimed only within one owner's transaction.** External effects (email, push, provider calls, transfers, file generation sent outside) are never part of an atomic claim. They are triggered post-commit through an outbox written in the same transaction.
*Check:* no requirement claims atomicity over an external effect.

**R18. Multi-owner operations are sagas.** Classify every step as `compensatable`, `pivot` or `retriable`. Order: compensatable steps, then the pivot, then retriable steps. Name the compensation for every compensatable step. Retriable steps must be idempotent.
*Check:* every operation spanning an external owner has a classified step list with compensations.

**R19. Every message is classified.** `assert` messages are sent only after the pivot, from committed state. `request` messages may precede the pivot and must have a timeout and a compensation. Every sender re-reads current state at send time and drops the message if it is stale (rescheduled time, changed status, superseded version).
*Check:* no assert message is triggered before its pivot; every request message has a timeout; every sender re-validates.

**R20. Every inbound external event is fully specified:** authenticity verification, idempotency key, tolerance of duplicates and reordering, and behavior when it arrives in an unexpected state (see R8).
*Check:* all four are present for each inbound event.

### F. External boundaries

**R21. Every external owner is in the boundary register.** For each: what crosses, whether the related invariant is `enforced` or `verified`, the reconciliation cadence, and behavior when events are lost.
*Check:* every external system, provider and human actor whose action changes state appears.

**R22. Priority inheritance.** If a requirement at priority P depends on data or a mechanism, that mechanism is at priority P or higher.
*Check:* no requirement depends on an input of lower priority.

**R23. Nothing is asserted to a person on unreconciled external data.** If data may be lost or delayed, the assertion waits for reconciliation or is explicitly labeled provisional.
*Check:* every assert message derived from external data names its reconciliation step or provisional label.

### G. Business rules

**R24. No authority-decided values in requirement text.** Every limit, rate, window, threshold or band is a named parameter in the parameter register, with effective dates and an authority reference. Requirement text refers to the parameter by name. Placeholder values are allowed only in the register, marked as placeholders.
*Check:* no business number appears in requirement prose except by parameter name.

**R25. Decisions snapshot the rules they used.** Every decision record (order, sanction, refund, earning, approval, payout) stores references to the parameter and policy versions applied, including terms shown to a customer at the moment of the decision.
*Check:* every decision entity lists its snapshot references.

**R26. Parameters and structure are separated.** Values that can change without code changing are parameters (tables, effective-dated). Logic variants (formulas, earning models, calculation methods) are versioned code, selected by a key stored in a parameter table. Structure (states, step sequences) lives in code.
*Check:* every configurable item is classified as parameter or structure; no structure item is presented as configurable data.

**R27. Authority limits are aggregate-aware.** Every limit states its aggregation scope (per transaction, per order, per customer, per day) so it cannot be evaded by splitting.
*Check:* every limit declares its scope.

**R28. Overrides are transitions.** Any rule that may be waived has an override transition with its own authority, mandatory reason and permanent record. Business invariants of this kind take the form "rule satisfied OR valid override recorded".
*Check:* every waivable rule has an override transition in the relevant state machine.

### H. Authorization and concurrency

**R29. Every transition names who may fire it.** Separation of duties is written as an invariant between actor fields (`approved_by <> created_by`) so it can become a database constraint.
*Check:* the actor column is complete; every maker-checker requirement has an actor-inequality invariant.

**R30. Every racing transition names its resolution.** For any transition that can race with another (capacity, booking, expiry vs callback, cancel vs start, concurrent edit): state the mechanism (conditional update, row lock, exclusion constraint, optimistic version) and what the losing side experiences.
*Check:* every concurrency register entry has a mechanism and a loser behavior.

### I. Data

**R31. The schema is derived from the registers.** Map each invariant to a database constraint where expressible (NOT NULL, CHECK, UNIQUE, foreign key, exclusion, deferred constraint trigger, revoked privileges for append-only tables). List invariants that cannot be expressed as constraints with their owning action and reconciliation.
*Check:* every invariant is either mapped to a constraint or listed with its alternative enforcement.

**R32. Deletion is reconciled with retention.** Every entity that can be deleted or anonymised has a plan for records that must outlive it, including how foreign keys from retained records continue to resolve (e.g. reference a pseudonymous party record rather than the personal record).
*Check:* every deletable entity referenced by a retained record has a resolution plan.

### J. Verification

**R33. Every calculation has worked examples.** Each formula or money movement has at least one concrete case with inputs and expected outputs, signed off by a domain owner. Internally consistent wrong formulas pass every other check; only examples catch them.
*Check:* every calculation has a signed-off example.

**R34. Contradictions are surfaced.** Where two requirements conflict (e.g. one claims atomicity over a notification, another says notifications never block the triggering action), report both IDs and do not silently pick one.
*Check:* contradiction list produced, even if empty.

---

## Part 3: Register templates

Produce each register as a markdown table with exactly these columns. Use stable IDs with the given prefixes. Every row cites the requirement IDs it derives from.

### 3.1 Ownership map
| Entity | Owning module | Written only by (actions) | Source reqs |
|---|---|---|---|

### 3.2 Invariant register (`INV-`)
| ID | Statement | Kind (safety / per-state / cross-entity / business) | Owner | Enforcement (type / db-constraint / owning-action / reconciliation) | Constraint or mechanism | Priority | Source reqs |
|---|---|---|---|---|---|---|---|

### 3.3 State machines (one per entity, `SM-`)
Transition table:
| From | To | Event | Actor | Guard | Effect | Concurrency rule | Failure guarantee |
|---|---|---|---|---|---|---|---|

Followed by:
- **Terminal states:** list with reason.
- **Per-state invariants:** state → required fields / forbidden fields.
- **External event coverage:** event × state matrix (transition or explicit rejection).
- **Coupled machines:** mapping table if applicable.

### 3.4 Timer register (`TMR-`)
| ID | Entity.state | Driver | Deadline field | Bound (parameter name) | Backstop | Fallback transition | Monitoring query | Source reqs |
|---|---|---|---|---|---|---|---|---|

### 3.5 Parameter register (`PAR-`)
| ID | Name | Classification (parameter / logic-variant-key) | Scope | Placeholder value | Authority | Effective-dated | Snapshotted on | Source reqs |
|---|---|---|---|---|---|---|---|---|

### 3.6 Authority matrix (`AUT-`)
| ID | Transition or action | Roles permitted | Limit (parameter) | Aggregation scope | Separation-of-duties invariant | Override path | Source reqs |
|---|---|---|---|---|---|---|---|

### 3.7 External boundary register (`EXT-`)
| ID | External owner | What crosses | Direction | Invariant enforced or verified | Inbound verification + idempotency key | Reconciliation cadence | Loss behavior | Source reqs |
|---|---|---|---|---|---|---|---|---|

### 3.8 Message register (`MSG-`)
| ID | Message | Class (assert / request) | Trigger | Pivot it follows (assert) or timeout + compensation (request) | Send-time revalidation | Channel via outbox | Source reqs |
|---|---|---|---|---|---|---|---|

### 3.9 Concurrency register (`CON-`)
| ID | Racing transitions | Shared state | Mechanism | Winner rule | Loser behavior | Source reqs |
|---|---|---|---|---|---|---|

### 3.10 Worked examples (`EX-`)
| ID | Calculation | Inputs | Expected outputs | Signed off by | Source reqs |
|---|---|---|---|---|---|

---

## Part 4: Procedure

Follow these steps in order.

1. **Inventory entities.** List every noun that has state or a lifecycle. Build the ownership map (3.1).
2. **Route requirements.** Apply R4 to every requirement sentence. Create draft register entries.
3. **Build state machines.** For every entity with a status, build the full table (R7). Fill the external event coverage matrix (R8). Declare terminals (R10). Add per-state invariants (R6). Build coupling maps (R12).
4. **Build the timer register.** For every non-terminal state, determine driver, bound, backstop and fallback (R13–R15).
5. **Classify multi-owner operations as sagas** (R18) and classify every message (R19).
6. **Build the boundary register** (R21) and apply priority inheritance (R22).
7. **Extract parameters and authority** (R24–R29).
8. **Build the concurrency register** (R30).
9. **Map invariants to schema** (R31) and check deletion vs retention (R32).
10. **Collect worked examples** (R33), marking missing ones as open items.
11. **Run the checklist** (Part 5) and produce the report (Part 6).

When the spec does not contain the information needed to complete a register entry, do not invent it. Create the entry with the missing field marked `OPEN` and add it to the open-items list.

---

## Part 5: Checklist

Every item is pass or fail. Report failures with the entity or requirement IDs involved.

| # | Check | Rules |
|---|---|---|
| C1 | Every stateful entity has exactly one owner | R1 |
| C2 | Every multi-module operation names its orchestrator | R2 |
| C3 | Every duplicated fact has source, derivation, reconciliation | R3 |
| C4 | Every R4-matching sentence has a register entry | R4 |
| C5 | No P0 invariant is documented-only; constraint-expressible invariants are constraints | R5, R31 |
| C6 | Every status field has a complete eight-column transition table | R7 |
| C7 | Every external event is handled or rejected in every state | R8, R20 |
| C8 | No ambiguous actors in triggers | R9 |
| C9 | Exitless states equal declared terminal states | R10 |
| C10 | Every non-terminal state has a system-controlled exit or timer | R11, R13 |
| C11 | Every coupled pair of machines has a complete mapping | R12 |
| C12 | Every timer has deadline field, monitoring query, and backstop where event-conditioned | R14, R15 |
| C13 | Every scheduled job has catch-up, idempotency, heartbeat | R16 |
| C14 | No atomicity claim spans an external effect | R17 |
| C15 | Every external saga has classified steps and compensations | R18 |
| C16 | No assert message precedes its pivot; every request has a timeout; every sender revalidates | R19 |
| C17 | Every external owner is in the boundary register with loss behavior | R21 |
| C18 | No requirement depends on a lower-priority input | R22 |
| C19 | No assertion to a person rests on unreconciled external data | R23 |
| C20 | No authority-decided number in requirement prose | R24 |
| C21 | Every decision record lists its snapshots, including customer-facing terms | R25 |
| C22 | Every configurable item is classified parameter or structure | R26 |
| C23 | Every limit declares its aggregation scope | R27 |
| C24 | Every waivable rule has an override transition | R28 |
| C25 | Every transition has an actor; every maker-checker has an inequality invariant | R29 |
| C26 | Every racing transition has a mechanism and loser behavior | R30 |
| C27 | Every deletable entity referenced by retained records has a resolution plan | R32 |
| C28 | Every calculation has a signed-off worked example | R33 |
| C29 | Contradictions listed | R34 |

---

## Part 6: Output format

Produce a single markdown document with these sections, in order:

1. **Summary.** Counts: entities, invariants, state machines, timers, parameters, boundaries, messages, concurrency entries. Checklist result: passed / failed / total.
2. **Critical findings.** The failures most likely to ship as silent defects, ranked. Prioritize: dead or stuck states, false atomicity claims, assert messages before pivots, missing late-event handling, priority inversions, money or trust decisions resting on unreconciled data. For each: rule ID, requirement IDs, what goes wrong in production, and the proposed fix.
3. **Registers 3.1–3.10.**
4. **Checklist results.** All 29 checks with pass/fail and failure details.
5. **Contradictions.** Pairs of conflicting requirement IDs with explanation.
6. **Open items.** Every `OPEN` field, grouped by the owner who must decide (business, finance, legal, operations, engineering).
7. **Test plan.** Produced per Part 8: the `TST-` table, the fault-injection matrix, the mutation plan, and test checklist results (C30–C39).

---

## Part 7: Common defect patterns

Look for these specifically; they recur across specs.

1. **Generic-actor trigger blocks a specific-actor transition.** A state advances when "any participant" acts, which removes the state from which "specific actor failed to act" could be detected. (R9)
2. **Dead dispute state.** An entity enters `disputed`, `on_hold` or `under_review` with no outgoing transitions. (R10, R11)
3. **Late external event with no legal transition.** An expiry moves an entity to `cancelled`, and a later successful callback has nowhere to go. Money is taken with no record path. (R8, R20)
4. **Retry against a terminal state.** A requirement says a failed operation can be retried without duplication, but the failed state is terminal. (R8, R34)
5. **False atomicity.** A requirement bundles database changes and outbound messages into one "atomic outcome". (R17)
6. **Premature assertion.** A failure or success message is sent on the first external event, before reordering or reconciliation could correct it. (R19, R23)
7. **Stale scheduled message.** A reminder queued with an old payload fires after the underlying event moved. (R19)
8. **Event-conditioned release with no backstop.** Money, access or status waits on an event (a session, an approval) that may never occur. (R15)
9. **Priority inversion.** A P0 decision depends on a P1 reconciliation or data source. (R22)
10. **Live policy instead of snapshot.** A customer-facing term (refund window, cancellation policy) is read from the current configuration instead of the version shown at purchase. (R25)
11. **Splittable limit.** A per-transaction authority limit with no aggregate, evadable by several smaller actions. (R27)
12. **Anonymisation breaks references.** Retained financial or legal records point at a personal record that deletion erases. (R32)
13. **Check-then-act in application code.** Uniqueness or capacity enforced by reading then writing, instead of a constraint or conditional update. (R30, R31)
14. **Undeclared coupled states.** One entity's state changes (order refunded, disputed) with no specified effect on dependent entities (enrolment, earning). (R12)

---

## Part 8: Deriving the verifier layer

The registers describe what must be true. Tests make it executable. This part turns every register into tests **before implementation begins**, so the code is built against a verifier that was derived from the spec, not from the code.

This is not incremental red-green TDD. It is acceptance-first verification: the test suite is the executable form of the registers.

### 8.1 Verifier rules

**V1. Independence.** Tests are generated from the registers and the spec only. The agent generating tests must not see implementation code, and the agent implementing code must not author or modify tests. A test derived from code confirms whatever the code does.
*Check:* the test plan cites only register and requirement IDs as its source.

**V2. Strength.** Every test must be shown to fail against a deliberately broken implementation. Tests that survive mutation (Part 8.6) are vacuous and must be strengthened or removed.
*Check:* mutation score per register meets the agreed threshold; every surviving mutant is listed.

**V3. Traceability.** Every test cites the register entry it protects (`INV-`, `SM-`, `TMR-`, `CON-`, `EXT-`, `MSG-`, `PAR-`, `AUT-`, `EX-`). Every register entry has at least one test.
*Check:* no test without a register reference; no register entry without a test.

**V4. Determinism.** Tests inject the clock, random seeds and external responses. No test depends on wall-clock time, network access or execution order. Property-test seeds are recorded so failures reproduce.
*Check:* no direct clock reads, real network calls or unseeded randomness in the suite.

**V5. Enforcement is tested at its declared level.** An invariant declared `db-constraint` is tested by writing directly to the database, bypassing the application. An invariant declared `owning-action` is tested through the action. An invariant declared `reconciliation` is tested by creating the violation and asserting the reconciliation detects it.
*Check:* each invariant's test matches its enforcement level from the invariant register.

**V6. Change propagates through IDs.** When a requirement or register entry changes, every test citing it is regenerated or reviewed. Tests are never edited to pass without a corresponding register change.
*Check:* every test modification references a register change.

### 8.2 Derivation rules by register

**T1. State machines (`SM-`)**
- One test per permitted transition: from-state, event, actor, guard satisfied → to-state, effect (postcondition) holds, per-state invariants of the new state hold.
- One test per guard failure: guard violated → transition rejected, state unchanged.
- One test per forbidden transition: every (state, event) pair not in the table → rejected with the specified behavior.
- One test per actor restriction: wrong actor → rejected (see T9).
- For every external event: one test per state from the coverage matrix, including states where it arrives late or duplicated.
- For every coupled machine: drive the source machine through each state and assert the mapped state of each dependent machine.

**T2. Invariants (`INV-`): stateful property tests**
- Build a model from the transition tables: states, events as operations, guards as preconditions.
- Generate random sequences of operations (including concurrent and external events) against the real implementation.
- After **every** step, assert every invariant in the register holds.
- On failure, shrink to the minimal failing sequence and record it as a permanent regression test.
- Minimum: one property suite per aggregate owner, covering all its invariants together, since violations usually arise from interactions.

**T3. Timers (`TMR-`)**
- Enter each waiting state, advance the injected clock past the deadline, run the scheduler: assert the fallback transition occurred.
- Advance to just before the deadline: assert nothing fired.
- Skip multiple periods without running the scheduler, then run once: assert catch-up processed everything due.
- Run the scheduler twice for the same period: assert idempotency.
- For event-conditioned timers: suppress the event entirely and assert the backstop fires.
- Assert the monitoring query returns zero rows after every scheduler run.

**T4. Concurrency (`CON-`)**
- For each racing pair: execute both operations concurrently against the same object, many times with varied interleavings.
- Assert exactly one winner per the winner rule, the loser experiences the specified behavior, and all invariants hold.
- Capacity and booking races: N concurrent requests for M < N places → exactly M succeed.

**T5. External boundaries (`EXT-`): fault injection**
For every inbound event, apply each fault in the fault-injection matrix (8.5) and assert the resulting state is correct:
- duplicate delivery → effect applied exactly once;
- out-of-order delivery → final state correct;
- late delivery after a timeout transition → the specified late-event path, never an unhandled error;
- lost delivery → reconciliation restores the correct state within its cadence;
- invalid signature → rejected, no state change.

**T6. Messages (`MSG-`)**
- For each `assert` message: fail the transaction at the pivot and assert no outbox row exists; commit and assert exactly one outbox row.
- For each `request` message: let its timeout expire and assert the compensation ran.
- For each sender: change the underlying state after queuing (reschedule, cancel, supersede) and assert the stale message is dropped at send time.
- Retry the sender: assert no duplicate delivery.

**T7. Schema (`INV-` with `db-constraint`)**
- For each constraint: attempt the violating write directly in the database and assert it is rejected.
- For append-only tables: attempt `UPDATE` and `DELETE` with the application's database role and assert both are refused.
- For deferred constraints: violate inside a transaction and restore before commit (must succeed); violate and commit (must fail).

**T8. Parameters (`PAR-`)**
- For each effective-dated parameter: create two versions with different values and evaluate decisions as-of dates in each period; assert each uses its own version.
- For each snapshot: change the parameter after a decision and assert the decision record and its outcomes still use the snapshotted version.
- For logic-variant keys: assert each historical key still produces its original result on its original inputs.

**T9. Authority (`AUT-`)**
- For each transition: each permitted role succeeds; each other role is rejected.
- For each limit: at the limit succeeds; one minor unit over is rejected or routed to override.
- For each aggregate limit: split an over-limit amount across several actions under the per-action limit and assert the aggregate rule rejects the excess.
- For each separation-of-duties invariant: same actor in both roles → rejected.
- For each override: without reason → rejected; with authorized actor and reason → succeeds and is recorded.

**T10. Worked examples (`EX-`)**
- One golden test per worked example: exact inputs, exact expected outputs, in integer minor units where money is involved. No tolerance unless the example states one.

### 8.3 Test plan template (`TST-`)

| ID | Protects (register refs) | Type (transition / guard / forbidden / property / timer / race / fault / message / constraint / parameter / authority / golden) | Setup | Action | Expected | Enforcement level tested | Priority |
|---|---|---|---|---|---|---|---|

Priority of a test equals the highest priority of the register entries it protects (priority inheritance, R22).

### 8.4 Stateful property testing guidance

- **Model:** the transition tables are the model. The test harness holds a simple reference model of expected state alongside the real system.
- **Commands:** each event in the transition tables is a command with a precondition (its guard, as far as the model can evaluate it) and a postcondition (its effect).
- **Checks:** after each command, compare real state to model state and assert every invariant.
- **Generation:** include external events, clock advances and concurrent command pairs in the command set, not just user actions.
- **Shrinking:** keep the minimal failing sequence as a named regression test citing the violated register entry.
- **Budget:** run a small number of sequences on every change and a large number nightly.
- Suitable libraries include Hypothesis (Python), fast-check (JavaScript/TypeScript), QuickCheck and its ports, and Eris (PHP). Use whichever matches the implementation language.

### 8.5 Fault-injection matrix

Produce one row per inbound external event.

| Event | Duplicate | Reorder | Late (after timeout) | Lost | Bad signature | Expected final state per fault |
|---|---|---|---|---|---|---|

A cell may only be marked not applicable with a stated reason.

### 8.6 Mutation plan

Apply these mutation operators to the implementation. Each must be killed by at least one test that cites the relevant register.

| Operator | What it breaks | Should be killed by |
|---|---|---|
| Remove a guard | Precondition enforcement | T1 guard tests |
| Flip or loosen a comparison | Limits, thresholds, capacity | T1, T4, T9 |
| Skip an assignment in an effect | Postconditions | T1 effect assertions, T2 |
| Drop a database constraint | Constraint enforcement | T7 |
| Remove an idempotency check | Exactly-once processing | T5 duplicate, T6 retry |
| Remove a conditional-update clause | Race resolution | T4 |
| Move an outbox write before the pivot | Premature assertion | T6 |
| Remove send-time revalidation | Stale messages | T6 |
| Change a timer bound or remove a backstop | Liveness | T3 |
| Read the current parameter instead of the snapshot | Decision snapshots | T8 |
| Remove an actor or role check | Authorization | T9 |
| Remove a reconciliation step | Boundary verification | T5 lost-delivery |
| Swap a forbidden transition into the allowed set | State machine completeness | T1 forbidden tests |

Language-specific mutation tools (for example Infection for PHP, Stryker for JavaScript/TypeScript, mutmut for Python) cover generic operators; register-specific operators above may need targeted scripts.

### 8.7 Test checklist

| # | Check | Rules |
|---|---|---|
| C30 | Every register entry has at least one test; every test cites a register entry | V3 |
| C31 | Test plan derived without reference to implementation code | V1 |
| C32 | Every permitted, guarded and forbidden transition is tested | T1 |
| C33 | Every aggregate owner has a stateful property suite checking all its invariants after every step | T2 |
| C34 | Every timer has deadline, pre-deadline, catch-up, idempotency and backstop tests | T3 |
| C35 | Every racing pair has a concurrency test | T4 |
| C36 | Fault-injection matrix complete for every inbound event | T5, 8.5 |
| C37 | Every message has pivot, timeout (requests) and staleness tests | T6 |
| C38 | Every invariant is tested at its declared enforcement level | V5, T7 |
| C39 | Mutation plan executed; surviving mutants listed and resolved | V2, 8.6 |