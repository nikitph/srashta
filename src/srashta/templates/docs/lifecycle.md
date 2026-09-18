# Lifecycle — who does what, where

The gap this document closes: everything upstream produced artifacts, but nothing said where they
live, who creates the repo, or how a fresh session knows what has already happened.

## The missing actor: the repo

**The project repo is the handoff medium.** Not a chat, not a zip, not a session container.

A planning session is ephemeral — a new one starts with no memory of the last. An orchestrator runs
on a different machine on a different day. A human comes back after a week. All three need the same
answer to "where are we?", and only a repo can give it.

So: spec, brand, contracts, tickets, briefs, config, execution state and retrospectives all live in
git. Every actor reads the repo. Nobody reads a conversation.

```bash
python3 pipeline/status.py
```

prints what is done, what is next, and **whose turn it is**. That is the session-continuity
interface. Run it first, always.

## The three actors

| Actor | Is | Does | Reads | Writes |
|---|---|---|---|---|
| **Planning session** | a chat with an agent | spec, brand, contracts, decomposition, retrospective | the repo | the repo |
| **Orchestrator** | Multica, Symphony, a loop | claims tickets, spawns workers, watches CI, merges | `build/handoff/phase-N/` | `state.json`, telemetry, code |
| **You** | you | answer blockers, approve contracts, review design and journeys | whatever you like | approval markers |

Workers sit under the orchestrator and see one brief each. They are not an actor at this level.

## Bootstrap — resolving the circularity

Contracts are built by wave-0 tickets → which need an orchestrator → which needs a repo with a
working stack. That is circular unless someone breaks it, so **`pipeline/init.py` breaks it**:

```bash
python3 pipeline/init.py acme --dest ../acme
```

creates the repo, copies the pipeline and constitution, scaffolds the stack, and makes the first
commit. This runs **once**, before any ticket exists. Everything after it is ordinary.

## The sequence

Each numbered item is one sitting. Between any two, everything is on disk.

**1 · Init and shape** — *planning session*
You describe the idea. The session runs `init.py`, pushes the repo, and works the idea into a
problem statement, actors, journeys and non-goals.
→ repo exists, `spec/` has a draft.

**2 · Spec** — *planning session, possibly several*
`/spec-authoring`. Ends when `lint_spec.py` passes structurally.
→ `spec/product-prd.md` committed. **You read it** — a linter finds an inconsistent spec, never a
wrong one.

**3 · Brand** — *planning session, forks off partway through 2*
`/brand-identity`. Three or four decisions from you.
→ `brand.yaml` committed.

**4 · Readiness** — *planning session*
`/spec-readiness`. Parses, audits, derives modules, assigns phases.
→ `build/requirements.assigned.json`, `config/defaults.yaml`, blockers recorded in
`project.yaml`.
→ **YOUR TURN**: answer only the blockers gating phase 0. Set `answered: true`.

**5 · Phase 0 contracts** — *planning session*
`/phase-decomposition` step 4. Includes writing the state machines the spec omitted.
→ `contracts/phase-0.md`.
→ **YOUR TURN**: read it, then `touch contracts/phase-0.approved`. That file *is* the gate — a
marker in the repo, not an approval in a chat, so a later session can see it happened.

**6 · Design system** — *planning session*
`/design-system-bootstrap`. Produces tokens, patterns, `DESIGN.md`, CI checks, the `/_design`
evidence page, registered as contract `C-00`.
→ **YOUR TURN**: look at two screenshots.

**7 · Tickets** — *planning session*
`/phase-decomposition` step 6, then `export.py 0`.
→ `build/handoff/phase-0/` — manifest, tickets, briefs. **This is the handoff artifact.**

**8 · Execution** — *orchestrator*
Imports the handoff, or polls `eligible.py`. Claims, spawns, merges, writes `state.json` and
telemetry.
→ **YOUR TURN** at contract PRs, integration PRs, and the first couple of built screens.

**9 · Exit gate and retrospective** — *planning session*
Integration journeys green → `/build-retrospective` reads the telemetry.
→ `retrospectives/phase-0.md`, and corrections split three ways.

**10 · Next phase** — back to step 5 with the corrections applied.

## The handoff moment, precisely

Step 7 → 8. One directory, committed and pushed:

```
build/handoff/phase-0/
  manifest.json    repo, phase, exit gate, conventions, routing, telemetry required
  tickets.json     the graph
  packs/<ID>.md    one brief per ticket
```

The planning session's last act is to push it and say so. The orchestrator's first act is to read
`manifest.json`. Nothing else crosses.

## Coming back cold

A new planning session, weeks later, with no memory: clone or pull, run `status.py`, and it says
what to do and which skill to invoke. That is the whole onboarding.

The same is true for you, and for a second person, and for a different agent.

## Where each human gate physically happens

| Gate | Where | Recorded as |
|---|---|---|
| Blocker answers | the chat | `answered: true` in `project.yaml` |
| Contract approval | reading `contracts/phase-N.md` | `contracts/phase-N.approved` |
| Design review | two screenshots in the chat | merged `C-00` PR |
| Contract and integration PRs | your git host | merge |
| Phase exit | integration journeys green | `retrospectives/phase-N.md` |

Every one leaves a mark in the repo. A gate that only happened in a conversation did not happen.

## If a planning session cannot reach the repo

It works in a container and hands you a patch or a zip; you commit. Slower and easier to lose, so
prefer giving the session push access. The method does not change either way — the repo is still
the state.
