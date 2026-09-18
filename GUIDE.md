# Srashta operating guide

[← Project overview](README.md) · [Interactive walkthrough](https://nikitph.github.io/srashta/)

A Python CLI for **idea → specification → approved contracts → bounded tickets → verified implementation → frozen API**.

The CLI parses, derives, validates and records evidence. Your planning agent and you make product decisions. Your external orchestrator claims work, launches isolated workers, reviews and merges it. Srashta never invokes a model.

## Install this release

Python 3.10+ on macOS/Linux. From this source directory:

```bash
python -m pip install .
srashta --version
```

You can also build a wheel with `python -m build` and install it with `pipx install dist/srashta-0.1.2-py3-none-any.whl`.
Srashta has not been published to PyPI.

## Start a project

```bash
srashta init my-api --run-scaffold
cd my-api
srashta status
```

Scaffolding requires Git, PHP 8.3+, and Composer. It creates the Laravel React starter, installs API routing, Scramble and Pest, and then adds planning files. The API workflow does not require a frontend build. Without `--run-scaffold`, init creates a planning repository only. Existing nonempty destinations are rejected. Init leaves the first commit to you.

Configure `project.yaml`, author the specification, and follow `PROCEDURE.md`. Planning guides have discoverable entrypoints under `.claude/skills/<name>/SKILL.md` and `.agents/skills/<name>/SKILL.md`; both reference the same editable project guide.

## The working loop

```bash
srashta run                         # extract, lint, module analysis, assignment
# Planning agent writes contracts/phase-0.md; human reviews it.
srashta approve 0 --by YOUR_NAME
# Planning agent writes tickets/phase-0.json.
srashta waves 0
srashta validate 0
srashta packs 0
srashta export 0
# Commit the approved plan and generated graph before starting execution.
srashta eligible 0 --json
srashta worker 0 C-01 --dest /path/to/new-worker-input
```

The worker input contains one brief and selected committed application files, without the PRD, other briefs, events or Git history. The orchestrator must launch that input inside its own filesystem sandbox. A copied directory or Git worktree alone is not isolation. Workers return patches and test/brief feedback; the orchestrator records events in the authoritative repository.

After integrating a ticket's commits into the local checkout:

```bash
srashta verify 0 C-01 --base BASE_COMMIT
srashta event C-01 brief_feedback --phase 0 --data '{"sufficient":true}'
srashta event C-01 merged --phase 0 --data '{"head":"VERIFIED_COMMIT","reviewed_by":"REVIEWER"}'
```

`verify` reads ownership and test commands from the base commit, checks every changed path and commit message, and runs the configured verification commands on committed code. Contract and integration merges require a recorded reviewer. The event is a local execution record; remote PR approval/merge authority remains with your orchestrator and repository protections. Squash/rebase merges need verification of the resulting commit, since the original SHA no longer proves the merged result.

After every ticket has verified merge evidence and brief feedback, write the retrospective:

```bash
srashta close 0 --by YOUR_NAME
srashta api generate
# Commit generated output before subsequent verification/closure commands.
# Once every backend phase is closed:
srashta api freeze --by YOUR_NAME
srashta api check --base TRUSTED_BASE_COMMIT
```

## Sources and generated files

| Durable source/evidence | Regenerated views |
|---|---|
| `spec/`, `project.yaml`, `constitution.md`, `config/defaults.yaml` | `build/requirements*.json`, module analysis |
| `contracts/phase-N.md` and content-bound `.approved` receipt | `build/tickets/phase-N.json` |
| **`tickets/phase-N.json` — authored decomposition** | `build/context-packs/phase-N/`, `build/handoff/phase-N/` |
| `events/`, `evidence/`, `retrospectives/` | `docs/openapi.yaml` before freeze |

Deleting `build/` must not delete planning judgment or execution evidence. Rebuild with extract, assign, waves, packs, export. A contract excerpt in a ticket must exactly match text in the approved design. Updating the design invalidates its approval. Editing a derived graph or brief makes validation/export fail.

OpenAPI is generated from Laravel routes with Scramble. Tickets cannot own the generated contract. The installed CI workflow uses the validator from the PR base, checks ticket changes and API freeze, and uploads generated API/evidence artifacts. It has read-only repository permissions and does not push commits or post comments. The operator/orchestrator publishes reviewed generated output. Enable required checks and human review on the hosting service; init cannot configure those without a remote repository.

## Migration from 0.1.0 / 0.1.1

Install this version and run `srashta upgrade`. It preserves legacy `build/tickets/phase-N.json` under `tickets/`, retaining dependency edges and inherited blockers for review. Review those sources, refresh project guides, and regenerate outputs. Old empty approval markers require a real re-review with `srashta approve`. Upgrade does not invent missing verification evidence, apply new CI automatically, or certify an old phase as complete. After each clone, run `srashta bootstrap` to enable hooks.

## Other commands

- `gentests`: generate every permitted and forbidden state transition, including self-transitions. Bind the generated test adapter to your action implementation before running it.
- `trace ID`: follow requirement and ticket references.
- `skills --full`: inspect guide differences. `--sync` preserves local edits unless explicitly forced; `--promote` publishes a reviewable PR when you explicitly invoke it and configure a blueprint repo.
- `event --id KEY`: idempotent append; concurrent writes use a process lock. Event logs are Git-tracked history, not tamper-proof storage.

Glob ownership supports relative POSIX paths with `*`, `?`, `**` and `**/`. Unsupported bracket classes and path traversal are rejected. Overlap and containment are checked as pattern languages, not by matching one glob string against another.

## Verification and scope

```bash
python -m pip install -e . pytest jsonschema
python -m pytest -q
python examples/notes_demo.py /absolute/path/to/new-notes-demo
```

The example creates a real Laravel Notes API, executes Pest tests, records verified commits and fixture approvals, closes its phase and freezes generated OpenAPI. It is a scripted acceptance test, not a measurement of autonomous agent quality.

This release ends at backend/API freeze. Brand/design-system guides remain available as future-stage guidance; surface implementation, MCP generation, a hosted scheduler, deployment, OS sandboxing and model execution are outside this release. Semantic requirements quality and whether tests adequately capture intent still need review. The 10× brief-size target is advisory for small specifications, where fixed instructions dominate.

For provisional runtime settings, declare `config_key` on an unresolved blocker and run `srashta defaults` after editing `config/defaults.yaml`. Laravel application code reads through `App\Support\ProvisionalConfig::read('key')`. A blocked key raises unless the caller explicitly acknowledges it **and** the application is in `local` or `testing`. Production always raises. Direct raw-config access bypasses this application boundary and must be rejected in review. Recompile and commit the generated config when an answer changes.
