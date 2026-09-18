# The Procedure

A harness-neutral method for turning a product idea into agent-ready tickets, and for keeping the
resulting build honest. It assumes autonomous coding agents do the implementation and a human
supplies judgment at a small number of gates.

Nothing in this document is specific to a model, a vendor, or a coding tool. The enforcement lives
in `pipeline/` and `schemas/`. **Conformance means the validator passes**, not that an agent
followed prose. Any agent that can read a spec, write files, and run Python can execute this.

---

## Why this exists

An agent given a whole specification drifts. Several agents given the same specification invent the
same shared structures separately, each pass their own tests, and disagree at merge. The fix is not
a better prompt; it is an intermediate layer.

The method is assembled from established practice rather than invented:

| Element | Established as |
|---|---|
| Total coverage, one owner per requirement | WBS 100% rule + mutual exclusivity |
| Frozen contracts enabling parallel work | Design rules — Baldwin & Clark, *Design Rules* (2000) |
| Modules and cross-module flows | Information hiding (Parnas 1972); bounded contexts (Evans) |
| Dependency-derived waves | Topological layering; Parnas "uses" hierarchy |
| Requirement → ticket → test links | Requirements traceability matrix (ISO/IEC/IEEE 29148) |
| Acceptance criteria | EARS (Mavin et al. 2009); Specification by Example (Adzic) |
| Transition tables tested both ways | Model-based testing: transition tour + sneak path |
| Decisions with rejected alternatives | Architecture Decision Records (Nygard 2011) |
| Interfaces with in-memory fakes | Ports and adapters (Cockburn); test doubles (Meszaros) |
| Spec defect detection | Requirements smells (Femmer et al., *JSS* 2016) |
| Defaulting open questions to keep moving | Set-based concurrent engineering; last responsible moment |

Two elements are not covered by that literature, because it assumes a human consumer who can be
trusted to look things up and ignore the rest:

- **Bounded context packs.** Information hiding applied to the agent's context window. The agent
  receives its pack and nothing else.
- **Granularity calibration.** What size of unit one autonomous agent run completes reliably is an
  open empirical question, measured by step 7.

---

## The steps

### 0 — Shape (human-led)
Idea → problem statement, actors, primary journeys, explicit non-goals. No artifact schema; the
output is whatever feeds step 1.

### 1 — Author the spec
**Runs:** once per project. **Output:** a spec meeting `schemas/spec-conformance.json`.

Stable permanent identifiers, EARS acceptance criteria, a transition table per stateful object,
ADR-form decisions, an open-questions register with owners, working assumptions as placeholder
values, and a phase plan that names every domain. Prose rationale stays unconstrained — the spec
has human readers whose job is to notice a *wrong* requirement, which no linter can do.

**Gate:** `pipeline/lint_spec.py` passes.

### 2 — Brand identity  *(forks off step 1 once positioning and personas are settled)*
**Output:** `brand.yaml` conforming to `schemas/brand.schema.json`.

Does not wait for the finished spec. Must be complete before the design system freezes.

### 3 — Readiness audit
**Runs:** once per project. **Outputs:** `requirements.json`, `config/defaults.yaml`,
`audit.md`.

Every open question classified **blocker** (changes the shape of the system) or **parameter**
(changes a value, gets a default). Every parameter default recorded in one place so no ticket
hardcodes one. Spec defects reported, especially coverage gaps — domains the phase plan never
names.

**Gate:** human answers blockers gating the first phase. Everything else proceeds on defaults.

### 4 — Architecture map
**Runs:** once per project. **Outputs:** `dsm.json`, `modules.md`.

Module boundaries derived from a dependency structure matrix, with the requirement-domain prefix as
a prior. Disagreements between the two are the signal. Cross-module flows fall out of the matrix,
ranked by clusters touched; that ranking is the contract agenda.

### 5 — Phase plan
**Runs:** once per project. **Output:** `requirements.assigned.json`.

Every requirement in exactly one phase. Domain defaults plus per-ID overrides, each with a stated
reason. Asserted total.

### 6 — Phase decomposition
**Runs:** once per phase, when that phase starts.

**6a Contract design** — schema, state machines, actions, event payload schemas, interfaces with
fakes, config keys. Includes writing the state machines the spec omitted. **Human approval gate.**

**6b Contract build and freeze** — contract tickets implement it. Transition tests and
consumer-driven contract tests are *generated*, not written. Frozen on merge.

**6c Tickets** — waves derived from the dependency graph; one owner per requirement; exclusive file
ownership within a wave; acceptance tests from EARS criteria; blockers propagated; context packs
emitted.

**Gate:** `pipeline/validate.py` exits zero.

### 7 — Retrospective
**Runs:** at each phase exit gate. Reads the telemetry the orchestrator filled in during execution.
Answers five questions with numbers, and splits corrections three ways: this project's next phase,
the blueprint, the method.

---

## Who decides what

| Decision | Who |
|---|---|
| What to build, and the requirements | Human |
| Brand direction — 3 or 4 choices | Human |
| Blocker answers | Human, or whoever they route to |
| **Contract approval, per phase** | Human — the highest-leverage gate |
| Review gates: design review, first screens, integration journeys | Human |
| Everything else | Agents, bounded by the validator |

---

## Artifact flow

```
spec.md ──lint──► requirements.json ──┬──► dsm.json ──► modules.md
                                      │
brand.yaml ──► design-system ─────────┤
                                      ├──► requirements.assigned.json
config/defaults.yaml ─────────────────┤
                                      ▼
                         contracts/phase-N.md  (human gate)
                                      │
                                      ▼
                        tickets/phase-N.json ──► context-packs/*.md
                                      │              │
                                  validate.py        └──► one agent, one ticket
                                      │
                                      ▼
                            execution + telemetry
                                      │
                                      ▼
                          retrospectives/phase-N.md
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             next phase          blueprint           method
```

---

## Portability

The core is Python 3 and JSON. It has no dependency on any agent framework.

- **Inputs** are plain text and YAML.
- **Intermediates** are JSON validated against `schemas/`.
- **Context packs** are plain Markdown — any agent consumes them.
- **`tickets/phase-N.json`** is the orchestrator interface. Any system that can create a ticket,
  route it, and record five telemetry fields can drive this.

`adapters/` holds thin entry points per harness. They contain no logic. Replacing an adapter is the
whole cost of supporting a new agent.
