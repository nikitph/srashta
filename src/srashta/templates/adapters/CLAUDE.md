# Working in this repo

This project follows a fixed procedure for turning its specification into agent-ready
tickets. The rules are enforced by the `srashta` CLI, not by this file.

**Always start here:**

```bash
srashta status
```

It reads the repo and tells you what is done, what is next, and whose turn it is — yours,
a planning session's, or the orchestrator's. It also names the skill to invoke.

## If you are executing a ticket

Your complete brief is `build/context-packs/phase-N/<TICKET>.md`.

- **Do not read the specification.** The pack holds every requirement you need, in full.
- Touch only the files the pack lists as owned. Another agent owns the rest right now.
- The pack's acceptance tests are the definition of done. Write them as failing tests first.
- Read parameters from `config/defaults.yaml`. Never hardcode a value that appears there.
- **If a frozen contract needs to change, stop and file a contract-change ticket.** Do not
  edit it. A contract is frozen so other agents can rely on it while you work.
- If the pack carries a BLOCKED banner, do not start.
- Record what happened: `srashta event <TICKET> attempt_started|tests_failed|merged ...`

## If you are running a pipeline step

`srashta status` names the step and the skill. Stop at every human gate — a gate that only
happened in conversation did not happen, so each one leaves a marker in the repo.

## Commands

```
srashta status              where are we, whose turn
srashta run --phase N       the whole chain
srashta validate N          the gate — non-zero on any defect
srashta trace <id>          why does this exist / what breaks if it changes
srashta eligible N          what may be claimed right now
srashta event ...           append to the execution log
```

## Standing rules

Never hand-assign a wave — the graph derives them. Never give two feature tickets the same
requirement. Never widen a ticket's file ownership to dodge a dependency. Never weaken a
validator check to make a decomposition pass: the check is the specification.

Never hand-edit anything under `build/`. It is a derived view, regenerated from `spec/` and
`project.yaml`, and your edit will be silently discarded on the next run. Change the source.
