# srashta

**स्रष्टा** — the one who brings into existence.

Turns a product specification into agent-ready tickets, and keeps the resulting build
honest. It does bookkeeping and enforcement; your agent harness does the thinking.

```
srashta decides what is CONSISTENT.
your agent decides what is GOOD.
```

**This CLI never calls a model.** No API keys, no model config, nothing to pay for twice.
Every act of judgment happens in Claude Code, Codex, or whatever you have open, on your
own subscription.

---

## Install

```bash
uv tool install srashta        # or: pipx install srashta
# development:
git clone … && cd srashta && pip install -e .
```

## The loop

```bash
srashta init drona --dest ./drona
cd drona
srashta status            # ← the only command you need to remember
```

`status` reads the repo and says what is done, what is next, and whose turn it is —
yours, a planning session's, or the orchestrator's. It names the skill to invoke.

`init` also drops `CLAUDE.md`, `AGENTS.md` and the six skills into `.claude/skills/`, so
whichever harness you open in that folder already knows the procedure.

## Commands

| | |
|---|---|
| `init <name>` | create a project repo from the blueprint |
| `status` | where are we, whose turn |
| `run [--phase N]` | the whole chain, degrading rather than blocking |
| `extract` · `lint` · `dsm` · `assign` | the chain, one stage at a time |
| `waves N` | derive waves over the authored ticket graph, in place |
| `packs N` | one bounded context pack per ticket |
| `validate N` | **the gate** — non-zero on any defect |
| `export N` | handoff bundle for the orchestrator |
| `eligible N` | which tickets may be claimed right now |
| `gentests` | transition tests from a table (pest / pytest / vitest) |
| `event …` | append to the execution log |
| `trace <id>` | why does this exist / what breaks if it changes |
| `skills [--full\|--sync\|--promote]` | compare, pull down, or PR up to the blueprint |
| `upgrade` | migrate this project to the installed version |

---

## Architecture

1,576 lines across 18 modules. Nothing is clever; the value is in what is enforced.

| Module | Responsibility | You change it when |
|---|---|---|
| `common.py` | config load, paths, io | rarely |
| `extract.py` | spec text → `requirements.json` | a spec has an unusual layout |
| `lint.py` | requirements smells + structural gates | you add a quality rule |
| `dsm.py` | coupling matrix, module derivation, flow ranking | tuning clustering — fully self-contained |
| `assign.py` | requirement → one module, one phase | rarely |
| `waves.py` | wave derivation, blocker propagation, normalisation | the ticket schema changes |
| `packs.py` | context pack rendering | **most common iteration** — packs are the agent's whole world |
| `validate.py` | **the gate** | you add an invariant |
| `export.py` | handoff bundle | the orchestrator contract changes |
| `eligible.py` | claimable set from graph + merge state | scheduling semantics change |
| `events.py` | append-only execution log, derived counts | you add an event kind |
| `trace.py` | walk the chain up or down | you add an edge type |
| `gentests.py` | transition-tour + sneak-path tests | you add a test flavour |
| `init.py` | scaffold a project, drop adapters and skills | you add a template |
| `status.py` | detect state, decide whose turn | you add a lifecycle step |
| `run.py` | drive the chain, degrade, report decisions | you add a stage |
| `skills.py` | diff, sync down, promote up (opens a PR) | you change sync semantics |
| `cli.py` | dispatch, version pin guard | you add a command |

Everything project-specific lives in `project.yaml`. Nothing in `src/srashta/` knows what
a Laravel is.

### Data flow

```
spec/*.txt ──extract──> requirements.json ──assign──> requirements.assigned.json
     │                        │                              │
     └──lint──> gates         └──dsm──> dsm.json             │
                                                              ▼
              contracts/phase-N.md (authored, human-approved)
                                                              │
                     tickets authored ────waves N────────> tickets/phase-N.json
                                                              │
                                        ┌─────────────────────┼──────────────┐
                                     packs                 validate       export
                                        │                     │              │
                          context-packs/phase-N/*.md        GATE       handoff/phase-N/
                                                                              │
                                                              orchestrator ───┘
                                                                              │
                                                       events/phase-N.jsonl ──┘
```

---

## Layer separation

Business logic finishes server-side before any screen exists.

The reason is a verification asymmetry, not reuse. An endpoint has a precise contract, so
its EARS criteria map 1:1 onto tests and an agent verifies its own work. A screen carries
taste — layout, responsiveness, accessibility — which needs a human eye. Separating them
puts all the machine-verifiable work in one track and bounds the rest.

| Layer | Owns | Requires |
|---|---|---|
| `api` | `app/**`, `routes/api.php`, `database/**`, `tests/Feature/**` | nothing from the design track |
| `surface` | `resources/**`, `routes/web.php`, `tests/Browser/**` | contract `C-00`, and an `api` ticket beneath it |
| `coupled` | both — **by declaration only** | listed in `transport_coupled` |

**Backend first.** Every `api` phase runs to completion before any `surface` phase starts.
Phases declare `layer: api | surface`, and `status` asks for brand and the design system
at the **boundary between them** — never up front:

```
  next planning session: endpoints are done — settle brand identity  →  /brand-identity
```

The boundary carries a gate: `gate_artifacts: [docs/openapi.yaml]`. A surface phase will
not decompose until the API contract is published, because that contract is what the
screens are designed *against*. Hand it to whatever draws them — Stitch, Figma, a
designer — and the result matches endpoints that already exist, rather than an imagined
payload discovered to be wrong at build time. The same artifact generates the MCP server.

This is a stronger answer to "UI reveals requirement gaps late" than journeys alone:
the gap cannot open, because the design input *is* the implementation's own contract.

What this buys, in order of how much it matters:

- **Brand and the design system stop gating the backend.** They freeze at the api→surface
  boundary, not before phase 0.
- **A screen ticket is purely compositional.** Endpoints frozen, tokens frozen — so you
  can try three layouts and discuss them creatively without touching anything else.
- **An MCP server becomes a generated artifact**, not a build. Every product ships
  agent-operable.
- **Backend packs lose three sections** and gain a "server-side only" banner.

### The API contract is generated, and owned by nobody

`ci/openapi.sh` regenerates it from the routes; `ci/api-contract.yml` runs it on every PR
and commits it on merge. **No ticket owns `docs/openapi.yaml`** — the validator rejects
one that tries.

That is not tidiness. Tickets in a wave run concurrently with exclusive file ownership,
so if every api ticket regenerated the contract, every ticket in the wave would collide
over the same file — breaking the exact rule the concurrency model rests on. Generating
it in CI sidesteps that completely, and it also means an agent produces contract
documentation by writing ordinary Laravel code rather than by remembering to document
anything. (`dedoc/scramble` reads routes, form requests and resources; no annotations.)

Two useful consequences fall out:

- **Every PR carries an API diff**, posted as a comment. A response shape changing that
  the ticket did not set out to change is the single best review signal in the backend
  track — and it is the failure an agent is most likely to cause silently.
- **After the boundary the contract freezes.** `docs/.openapi-frozen` makes an
  unannounced change fail CI, because by then screens are built against it. A change
  becomes a contract-change ticket, like any other contract.

Two things make it real rather than aspirational. The constitution's **no business logic
in a controller** rule, checked by `ci/check-controllers.sh` — both controllers call the
same action, which makes the surfaces provably equivalent rather than merely parallel.
And **journeys**: every `api` ticket cites the journey step it makes possible, so
endpoints fall out of what a person does rather than out of the entity model. That is the
enforceable form of "the API is complete but the screen still can't be built."

Transport-coupled work — real-time channels, uploads, OAuth redirects, canvas sync — does
not decouple and is not forced to. It is exempt **by declaration**: a ticket claiming
`layer: coupled` whose module is not in `transport_coupled` fails validation.

## The memory rule

**Never ask an agent to remember. Either put it in the artifact it reads, or make the
need disappear.**

Most of this codebase is that rule applied. Context packs, frozen contracts,
`defaults.yaml` — all of it is memory the agent does not have to carry. `machines.yaml`
plus generated sneak-path tests means an agent *cannot* make an illegal state transition
rather than being told not to. The OpenAPI decision is the other half of the rule: rather
than reminding an agent to document its endpoints, generation from routes removes the
duty entirely.

Two places used to violate it, and `packs.py` now closes both:

**What the previous attempt hit.** The event log already held it; the pack did not render
it, so a retrying agent rediscovered the same failure from scratch. A retry now opens
with the acceptance tests that failed last time, any files it touched that it does not own
(named as a *decomposition* defect, since that is usually what it is), and whether a
contract-change ticket is outstanding. History is dropped once the ticket merges.

**Decisions already made.** An agent that does not know a choice was deliberate will
helpfully "improve" it back to the thing you rejected. `decisions:` in `project.yaml`
carries the ADRs from the spec — decision, rejected alternative, and what they constrain —
and each reaches the pack of every ticket it touches, with the instruction to raise it in
the pull request rather than quietly implementing the alternative.

That second one is cheap insurance against the most expensive kind of agent error: not a
bug, but a confident, well-tested reversal of something you settled months ago.

### Was the brief any good? — the routine capture

Every ticket closes by answering one question, injected into its `evidence` list by
`waves.finalise()` and required by the validator:

> a one-line statement of whether this brief was sufficient, naming anything you had to
> infer or could not find

This rides on evidence deliberately, and the reasoning matters. Asking an agent to
*notice* it lacks something and fire an event asks for calibrated uncertainty — the thing
models are worst at. Their default on missing information is to infer plausibly and carry
on, which is the same capability that makes them useful. So the agents that most need to
report a gap are precisely the ones that will not notice they have one.

A question it must answer to close the ticket gets answered. An action it must remember
to take does not.

It also captures the case no agent would ever raise separately, and the most useful one:
*"sufficient, but I had to infer the retention period."* `event --summary` groups those,
and flags anything two tickets both inferred as belonging in the template. It also flags
tickets that **merged without answering** — because if the orchestrator stops recording
it, the measurement dies silently.

### And when a ticket genuinely cannot proceed

`pack_insufficient` is the rare escalation, not the routine path — most of the time the
honest answer goes in the evidence above and the work continues. Use it when the ticket
cannot proceed at all:

```bash
srashta event T-15 pack_insufficient --data '{"needed": "…"}'
```

The pack is explicit that the alternative is not allowed: *do not read the specification
and do not go looking in other parts of the repository — that is scope, not constraint.*

`srashta event --summary` then groups the gaps, and flags any that more than one ticket
hit:

```
  brief was missing something  2
      T-15, T-21: the retention period for verification links   <- belongs in the pack template
```

**There is deliberately no query capability**, and a test asserts there is none. Two
reasons. The fix for an insufficient brief is a *better brief* — a lookup would let us
tolerate bad packs rather than fix them, and a curated template beats a retrieval every
time. And a query surface erodes by increments that each look reasonable: decisions, then
the glossary, then "related requirements", and the bounded context is gone.

Measure first. If this fires constantly, the log says exactly what to put in the
template.

## Shared resources

Disjoint `owned_files` is not the same as no contention. Three endpoint tickets with
entirely different files all need `routes/api.php`, and nothing in the ownership check
can see it.

**Prefer removing the contention over managing it.** A runtime lock converts a planning
failure into an invisible stall; an edge in the graph is reviewable and shows up in the
wave numbers. Three strategies, declared in `project.yaml`:

| Strategy | For | Effect |
|---|---|---|
| `fragment` | routes, config, providers, seeders | Each module owns `routes/api/<module>.php`; the aggregate loads them. **No edge, no serialisation** — the contention simply stops existing. |
| `contract_only` | lockfiles, migrations, the schema | Only a `C-` ticket may touch it. Shared structure is what contracts are *for*; a feature ticket changing it is already a contract violation. |
| `serialise` | the irreducible remainder | The validator adds an **explicit dependency edge at plan time**, deterministically ordered by ticket id and never inverting an existing edge. The graph stays a DAG. |

A ticket owning a shared path without declaring it in `touches` is a defect — undeclared
contention is invisible to every other check. Owning the aggregate instead of your
fragment is a defect, and the error names the fragment you should own instead.

And when a `serialise` resource chains more than three tickets, that is warned about
rather than accepted: *"Correct, but this is the signal to fragment the resource
instead."* The pain is made visible and pointed at its own fix.

Each brief says what it shares and what that means for it:

```
## Shared resources this ticket touches

- api_routes — write only `routes/api/identity.php`, never the aggregate.
  The aggregate loads the fragments.
- container — shared and serialised. The graph already orders you against the
  other tickets that touch it, so you have it to yourself. Keep your change minimal.
```

## Invariants — do not break these while iterating

1. **No model calls.** Ever. The moment srashta needs an API key it stops being
   harness-neutral.
2. **`build/` is derived.** Anything written there must be regenerable from `spec/` plus
   `project.yaml`. `validate` enforces this by regenerating into a shadow tree and
   comparing digests — so an artifact that is *not* deterministic cannot live there.
3. **`validate.py` is the conformance definition.** Weakening a check silently changes
   what "valid" means for every existing project. Adding or changing a check means
   bumping the version, so the pin guard forces a deliberate `srashta upgrade`.
4. **Waves are derived, never authored.** `wave_hint` exists only to measure drift.
5. **Events are append-only.** Never rewrite, never compact, never store a count beside
   the log — counts are derived in `events.derive()`.
6. **Output is decision-shaped.** Progress lines say what was decided; mechanics go to
   `build/run.log` and surface only under `--verbose`. Nobody should be reading about
   edge weights during a product design.
7. **Degrade, never block.** A stage that cannot do its job well falls back to something
   simpler and says so in one line. Only the human gates stop a run.

---

## Extending

**Add a validator check.** Append to `check()` in `validate.py`, pushing onto `E` for a
defect or `W` for a warning. Bump the version. Then re-run `validate` on every decomposed
phase of every project — a new check can turn a previously valid graph invalid, and you
want to see that deliberately.

**Add an event kind.** One entry in `events.KINDS`, one branch in `events.derive()`.
Existing logs stay readable: unknown kinds are ignored by `derive`, which is why the log
is append-only rather than versioned.

**Change a skill.** Skills carry judgment, not logic — the enforcement is in
`validate.py`, so a bad edit costs worse advice, never a broken pipeline.

Two flows, and they are not the same thing:

| | |
|---|---|
| **Local** | This project learns about itself. A retrospective's corrections are edited straight into `.claude/skills/`. No blueprint involved, nothing to sync. **This is the common case.** |
| **Cross-project** | Something one project learned is generally true. `skills --promote` opens a PR against the blueprint repo; another project later pulls it with `--sync`. |

Three copies exist:

| Copy | Affects | Edit it when |
|---|---|---|
| `templates/skills/*.md` | every **future** `init` | improving the blueprint (usually via a promoted PR) |
| `<project>/.claude/skills/*.md` | that project, and whoever clones it | a house rule, or a retrospective's correction |
| your agent's own skill store | chat sessions outside any project | — |

`init` copies rather than symlinks, so blueprint changes do not reach existing projects
by themselves.

**The hazard is that `--sync` overwrites.** Local edits carrying your own retrospective's
findings would be silently discarded, so sync names them, quotes them, and refuses until
you pass `--force` — with a nudge to `--promote` them first. A skill change is *not*
retroactive (unlike the version pin: tickets already written and contracts already frozen
are untouched), so the phase-boundary check is advisory rather than a refusal.

`--promote` needs `blueprint_repo` in `project.yaml` or `SRASHTA_BLUEPRINT_REPO`, plus
`gh`. It clones, branches, commits, pushes and opens a PR whose body carries the diff and
cites the project's latest retrospective — because a blueprint change without a rationale
is how blueprints rot.

**Change the context pack.** `packs.render()`. This is the highest-leverage file in the
codebase — it is literally everything an executing agent sees. Before adding a section,
ask whether an agent that lacked it would have failed; if not, leave it out. Pack bloat
is drift by another name.

**Support a new spec layout.** `project.yaml` already carries `id_pattern`,
`priority_pattern`, `body_start_line`, `footer_pattern`, `header_pattern`. Prefer a new
config knob over a code branch. `extract` refuses to proceed on a partial parse, so a
wrong pattern fails loudly rather than silently dropping requirements.

**Add a harness.** Copy `templates/adapters/AGENTS.md` into whatever form that tool reads
and teach `init` to write it. Adapters contain no logic — that is the whole cost of
supporting a new agent.

**Add a test flavour.** One template in `gentests.TEMPLATES` plus one row format in
`gentests.FMT`.

---

## Tests

```bash
pip install -e . && pytest -q          # 98 tests, ~1.6s
```

`tests/fixtures/` holds a 12-requirement synthetic spec, so the suite has no dependency
on any real PRD. Every invariant in the list above has a test that tries to break it:
missing owner, duplicate owner, file collision (equality *and* glob overlap), a ticket
resting on no contract, undeclared blocker inheritance, a hand-edited derived artifact,
a dependency cycle, a wrong wave hint, an unknown event kind.

Three tests exist because writing them found real bugs:

- `test_refuses_a_partial_parse` — the completeness check was validating the configured
  id pattern against *itself*, so a too-narrow pattern could silently drop a whole domain
  and still report success. `extract` now also scans with a generic identifier shape and
  fails on any family the pattern misses. This is the bug that dropped `FR-AUTHZ`.
- `test_chain_runs_clean` — stages are imported dynamically, so a broken import stays
  invisible until that stage runs. The end-to-end tests exercise every stage for real.
- The `assign` tests — `die()` called `sys.exit(1)`, discarding its own message.

When you add a check, add the test that trips it. The suite is the only thing standing
between an iteration and a silently weaker gate.

## What a review found, and what changed

Two independent reviewers — one on requirements quality, one adversarial — read the
specification and the code. Seven defects in shipped code, each of which made the tool
**assert something false**. All seven now have a regression test in
`tests/test_regressions.py` that was written before the fix and failed.

| Defect | Was | Now |
|---|---|---|
| Glob-vs-glob ownership | `fnmatch` both ways missed intersecting globs — `app/Models/*.php` and `app/*/User.php` both own `app/Models/User.php`, and validation passed | Real intersection, with a witness path in the error |
| Cross-wave scheduling | `eligible` released wave N+1 while wave N was in flight, printing "all concurrent — disjoint file ownership" when nobody had checked | A wave is not released until every ticket before it is done |
| Drift detection | A bare `except` returned "no drift" — a broken spec path plus a hand-edited artifact reported PASSED | An unverifiable artifact is a defect, and says why |
| Retry history | A bare `except` around the event read dropped every brief's history on one truncated line, silently | Refuses to write briefs and names the log to repair |
| `run` propagation | A stage returning non-zero printed a checkmark and the chain continued | A non-zero return is a failure |
| Approval gate | `contracts/phase-N.approved` was written, displayed, and **read by no gate** — a phase shipped unapproved | `validate` and `packs` both refuse without it |
| Derived waves | `waves.finalise()` **had no caller**; it was invoked by a markdown instruction, so a hand-written file skipped cycle detection and blocker propagation | Tickets carry a derivation stamp, and validate re-derives and compares |

The pattern worth keeping: every one of these reported success. Four were bare excepts or
unchecked returns; three were rules that existed in prose and nowhere in code. That is the
argument for `NFR-040` — a check the method relies on must be executable, not documented —
and for `NFR-041`, which requires a test that tries to violate it.

## Known gaps

- **`max_acceptance_tests: 12` is a guess.** The correct ticket size for one autonomous
  agent run is unmeasured. `events/` is the instrument that will replace it with a number
  after the first real phase.
- **`dsm` confidence thresholds are hand-tuned** on one spec. They self-assess and fall
  back to domain grouping, so a bad matrix degrades rather than misleads — but the
  thresholds deserve a second corpus.
- **`trace` shells out to `git log --grep`.** Fine for now; it assumes commit messages
  carry the ticket id, which nothing yet enforces. A CI check belongs there.
- **Python is an accident of who wrote it.** Every interface is a file against a published
  schema, so a rewrite (Laravel Zero is the likely target) keeps every existing project
  working — swap the binary, re-run `validate`.

## Method

`src/srashta/templates/PROCEDURE.md` is the method, harness-neutral.
`templates/docs/` covers the lifecycle, orchestration, spec rules and provenance.
`init` copies them into each project so the repo is self-describing.
