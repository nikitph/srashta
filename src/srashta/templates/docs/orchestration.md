# Orchestration — where a scheduler plugs in

## Two things, not one

"Master agent" conflates two jobs that should stay apart.

**The orchestrator** (Multica, Symphony, or a loop you write) is a *scheduler*. It claims eligible
tickets, opens a workspace, spawns a worker, watches CI, moves state, retries on crash. It does not
reason about the product, and it should not: **eligibility is a pure function of the ticket graph
plus merge state.** `pipeline/eligible.py` computes it, and it needs no model.

**The worker** (Codex, Claude Code, MiniMax — one per ticket) reads one context pack and writes
code. It is the only part that reasons, and it reasons about one ticket.

Conflating them is how "the master agent needs project context" becomes a question. The scheduler
barely needs any; the worker needs strictly less than you would expect.

## The seam: exactly two files

The pipeline is **build time**. It runs once per phase, writes artifacts, exits. The orchestrator
is **run time**. They meet here and nowhere else:

```
OUT   build/handoff/phase-N/manifest.json   what this run is, and the rules of engagement
      build/handoff/phase-N/tickets.json    the graph
      build/handoff/phase-N/packs/<ID>.md   one brief per ticket

IN    telemetry per ticket, written back into the ticket record
```

That seam is what makes the method harness-neutral. Integrating a new orchestrator means mapping
those two directions. Nothing else changes, and no part of the pipeline learns anything about it.

## What the orchestrator actually does

```
1  read manifest.json  — repo, phase, gate, conventions, routing hint
2  loop:
     claimable = eligible.py <phase> --state <state.json> --json
     for each claimable ticket, up to your concurrency limit:
        fresh workspace on branch <TICKET_ID>-<slug>
        spawn a worker with packs/<TICKET_ID>.md AS ITS ENTIRE BRIEF
        worker writes failing acceptance tests, then implements
        CI runs: unit, generated transition tests, consumer contracts, token lint, a11y
        open PR with the evidence the pack lists
        contract and integration tickets -> human review
        feature tickets -> auto-merge on green, UNLESS files outside owned_files changed
        on merge: state[ticket] = merged, write telemetry
3  when no ticket remains, run the phase exit gate, then build-retrospective
```

Every ticket in a claimable batch is safe to run concurrently: the validator has already proved
their file sets are disjoint. `max_concurrency` in the JSON output is the batch size.

## Rules the orchestrator must enforce

These cannot be left to the worker, because a worker under pressure will do the convenient thing:

- **Never claim a ticket with a non-empty `blocked_on`.**
- **Never hand a worker the specification.** The pack is the brief. A worker with the spec drifts.
- **A worker that needs a frozen contract changed stops.** It files a contract-change ticket; it
  does not edit and continue. Editing silently unfreezes a design rule every concurrent ticket is
  relying on.
- **A PR touching files outside `owned_files` does not auto-merge**, whatever CI says. That is the
  signal that the pack or the ownership assignment was wrong, and it is a retrospective input.
- **Telemetry is not optional.** Without it the retrospective is opinion.

## Injecting Multica specifically

Multica is self-hosted and ticket-driven, so the mapping is direct:

| Multica concept | Comes from |
|---|---|
| Project / board | `manifest.project` + `manifest.phase` |
| Ticket | one record in `tickets.json` |
| Ticket body | `packs/<ID>.md`, verbatim — not a summary |
| Dependencies / blocked-by | `depends_on`, `blocked_on` |
| Ready-to-claim query | `eligible.py --json` → `claimable_now` |
| Concurrency limit | `max_concurrency` from the same call |
| Agent assignment | `manifest.routing_hint` keyed by `kind` |
| Definition of done | the pack's acceptance tests, plus green CI |
| Required attachments | the pack's evidence list |
| Custom fields to write back | `manifest.telemetry_required` |

Two ways to wire it, both small:

**Push** — an importer reads `tickets.json` and creates one Multica ticket per record, with the
pack as the body. Re-runnable: match on ticket id and update rather than duplicate.

**Pull** — Multica calls `eligible.py --json` on its poll interval and claims from
`claimable_now`. Slightly better, because the graph stays the single source of truth and Multica
holds only status.

Either way the importer is the *only* Multica-specific code in the system, and it lives in
`adapters/multica/`, never in the `srashta` Python package.

## Using a different orchestrator, or none

- **Symphony / Linear** — same importer shape; `adapters/codex/WORKFLOW.md` describes the state
  machine in Linear terms.
- **A markdown kanban** — `export.py --format markdown-kanban` writes one file per ticket with
  front-matter status. Enough for a local loop with no server.
- **By hand** — run `eligible.py`, open the named pack, do the work. The method degrades to a
  person without losing any of its guarantees.
