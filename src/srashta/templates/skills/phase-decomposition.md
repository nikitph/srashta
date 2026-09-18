---
name: phase-decomposition
description: Design and freeze one phase's contracts, then cut it into agent-ready tickets. Once per phase, when that phase starts.
---
# Phase Decomposition
Contracts are what Baldwin & Clark call *design rules* — visible parameters frozen early so hidden work proceeds in parallel. Without them every agent invents the shared pieces separately, passes its own tests, and disagrees at merge.

First confirm no blocker gating this phase is unanswered. A question with gates_phase blocks the whole phase. For a narrower unresolved choice, omit gates_phase and attach its blocker only to the affected tickets.

## Contract design — the highest-leverage gate
Schema (note binding negative constraints like "there is no type column"; agents reintroduce these). State machines as transition tables. Actions with signatures and single-writer paths. Events with payload **schemas**, not prose. Interfaces with in-memory fakes — **always a freezable Clock**, since anything with a TTL is untestable without one and tests that sleep flake. Config keys from `defaults.yaml`.

> **Check for machines the spec does not have.** Enumerate every stateful object in the phase and write the missing tables into `machines.yaml`. This is usually the highest-value output of the whole step.

End with what the contract deliberately does not decide, and why the schema accommodates either answer. Then **stop for human approval**; record approval with `srashta approve N --by NAME`; its receipt binds the design contents.

## Build and freeze
`srashta gentests` emits transition-tour and sneak-path tests from the tables — never hand-write them. Register a consumer contract per event listener. On merge, contracts are frozen: a feature ticket may *use* one and must never *change* one.

## Tickets
Author ids, titles, modules, requirements, dependencies, owned files and acceptance tests — then `srashta waves N` reads `tickets/phase-N.json` and writes the derived graph in `build/tickets/phase-N.json`: waves, contracts used, blocker propagation, and the edges that keep a shared resource uncontended. A graph that did not come from it is rejected, and nothing else can be checked until it does. Rules, all machine-checked: waves **derived** from the dependency graph, never assigned; exactly one *feature* ticket owns each requirement (contracts *support*, others *assert*); file ownership exclusive within a wave; acceptance tests are required (a reviewer checks their correspondence to EARS criteria); blockers propagate; every ticket rests transitively on a frozen contract.

### Shared resources — the contention file ownership cannot see
Exclusive file ownership does not mean no contention: three endpoint tickets with three different controllers all need the route table, and every ownership check passes while they collide. Declare each one in `project.yaml` under `shared_resources`, and list it in a ticket's `touches`.

Pick the strategy in this order, because the first two cost nothing and the third costs a wave:

| Strategy | Use it when | What it does |
|---|---|---|
| `fragment` | the file can be split per module and an aggregate can load the pieces | each ticket owns `routes/api/{module}.php`; no edge, no ordering, no conflict |
| `contract_only` | the structure is shared design, not per-ticket work | a feature ticket touching it is a defect; it belongs to a contract ticket |
| `serialise` | genuinely one file, genuinely shared | `waves` adds real dependency edges ordering the tickets, deterministically and without inverting an existing edge |

Never wait at run time for a lock. Contention is a planning fact; an edge is reviewable before anything runs, shows up in the wave count as the cost it is, and keeps the graph a DAG. If serialising chains more than three tickets, that is the signal to fragment instead — the validator says so.

Then `srashta packs N` and `srashta validate N`.

If the phase declares `gate_artifacts`, they must exist before it decomposes — a published contract is not something to design tickets against from memory.

**Expect the validator to fail, and read each failure as a real defect.** In calibration it failed three times: wave/dependency contradictions, a file collision between concurrent tickets, then seven requirements no ticket implemented. A decomposition that passes first time has not been tested.

Finally `srashta export N`.

Every contract ticket needs `contract_context`: a bounded, exact excerpt from the approved design, copied into dependent briefs. Commit the plan before the first worker starts. Never put authored ticket judgment only in build/.
