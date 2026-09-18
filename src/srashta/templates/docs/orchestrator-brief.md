# Orchestrator contract

Read `build/handoff/phase-N/manifest.json` and `tickets.json`. Verify the per-brief SHA-256 values. Re-export if planning inputs changed. Handoff bundles are for the orchestrator, not whole-worker prompts.

1. Ask `srashta eligible N --state state/phase-N.json --json` for eligible work. Atomically claim work in your own scheduler. The CLI reports eligibility; it does not implement distributed claims or leases.
2. Export a worker directory with `srashta worker N TICKET --dest NEW_DIRECTORY`. Launch only that directory in a filesystem sandbox without access to the authoritative checkout. There is one `BRIEF.md`, selected committed application context, and `WORKER.json`. No `.git` or planning archive is included. Install dependencies in the sandbox as needed; preserve the source commit from WORKER.json.
3. Record attempt events in the authoritative checkout. Use stable `--id` keys for retried event deliveries. Capture tests, missing context, out-of-scope changes, review rounds and brief feedback. Repair missing context through planning and regenerate the brief.
4. Apply the returned patch to a ticket branch. Run `srashta verify N TICKET --base BASE` after committing the final code. If merge/rebase changes its commit, verify the resulting commit again. Do not infer an unknown remote merge outcome as success; reconcile it first.
5. Obtain required review and CI on the hosting service. Contract and integration tickets require human review. Record brief_feedback, then merged with the verified head and reviewed_by where required. Preserve evidence and event history in Git. The CLI checks local commit ancestry and evidence; it does not query your remote PR service.
6. At a phase boundary, obtain the retrospective, close the phase and commit the receipt. Generate/publish the API artifact under orchestrator ownership. After every API phase closes, record an approved API freeze.

The scheduler, worker sandbox, remote CI/merge protection and handling ambiguous remote outcomes are responsibilities of the external orchestrator. Do not present a handoff export as an executed project.
