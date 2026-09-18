# 0.1.2 — local release, 18 September 2026

Repair of the supplied 0.1.1 implementation. Artifact schema version 2.

- Preserve authored ticket graphs under tickets/; derive disposable build outputs and reject drift.
- Parse the supplied Markdown PRD, priorities and EARS criteria, including indented cross-references.
- Bind human approval receipts to contract contents; require exact contract excerpts in briefs.
- Check true glob intersection/containment and reject malformed/duplicate ticket records.
- Validate briefs before rendering and reject stale handoff exports; include pack hashes.
- Export one worker input without PRD/history; require the external orchestrator to sandbox it.
- Verify committed ticket diffs against baseline ownership, contract protection, trace IDs and project checks.
- Store locked, idempotent execution events and durable verification evidence outside build/.
- Require phase-scoped verified merges, brief feedback, a retrospective and checks before closing.
- Generate canonical OpenAPI, fail on missing model schemas, and enforce freeze against the trusted Git base.
- Scaffold Laravel in an empty staging directory before adding project metadata; install CI and clone-bootstrap hooks.
- Emit discoverable planning-skill entrypoints, preserving project edits in one canonical guide.
- Emit a guarded Laravel defaults reader for provisional configuration blockers.
- Generate all forbidden state transitions, including unlisted self-transitions.

Method clarifications: authored decomposition is source; trace is operator-only; a worker snapshot is not an OS sandbox; Git receipts are not authenticated identity; brief-size reduction is advisory for tiny specifications; CI publishes review artifacts rather than pushing commits. Full autonomous orchestration, surface work and deployment remain outside v0.1.
