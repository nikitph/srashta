# Revision 2 review

The supplied revision is now [PROCESS.md](PROCESS.md), with wording preserved and local links made repository-relative. The original is [revision 1](revisions/PROCESS-r1.md), with an [exact comparison](revisions/r1-to-r2.diff). This review proposes clarifications; it does not silently amend the supplied text or implement compiler behavior. The existing [Aarogya application](AAROGYA.md) predates A1–A6 and has not been revalidated against them.

The amendments address six useful weaknesses: self-granted exemptions, omitted inventory, stale evidence, overwritten decisions, loosely defined priority scope and unmeasured implementation guesses. Keep all six. Tighten their operational definitions before implementing validators.

## A1 — Approval must resolve to evidence; concurrency is a separate question

`origin: approved decision` must reference a decision revision and an approval record identifying authority, approved scope and content revision. The label alone cannot satisfy the gate. A proposal is not approval, and supplying this process document does not approve individual product exceptions.

Allow a previously approved foundation decision to satisfy an exemption when its scope and assumptions match. This preserves the fixed-foundation benefit without asking a human to approve the same stable-state classification for each product. A new or mismatched case stays open.

Remove the equivalence between **non-exclusive** and **no race obligation**. Multiple bill finalizations may all succeed while still contending for the same number series. Record concurrency applicability separately from allowed outcomes. Omitting a concurrency obligation on P0 requires the A1 approval; allowing multiple successes does not remove that obligation.

## A2 — Close a declared integration surface, with explicit scope and unknown-event handling

Bind catalogue closure to the selected provider product, API/event version, enabled features and subscription configuration. Account for events as handled, intentionally ignored or excluded by the approved integration scope. Version and review the scope so narrowing it cannot become an unrecorded exemption.

Pin a retained catalogue snapshot or content hash when the provider has no stable catalogue version. If no authoritative catalogue is available, record an unresolved completeness limitation rather than fabricating closure. Provider adapters that expose only synchronous operations need an explicit applicability classification for event coverage.

Every handled event needs coverage across each receiving machine's declared states. Appearing in one matrix is not sufficient if two machines consume it. Define unknown-event behavior too; pinning a catalogue does not specify runtime behavior for an unfamiliar event.

For example closure, require structured references to entities, states, events and parameters. Finding names in arbitrary prose is semantic extraction; resolving declared IDs is the mechanical check.

## A3 — Invalidation follows evidence inputs, not only capability labels

Represent each evidence claim with the capability and contract revisions, relevant dependency fingerprints, configuration, environment and usage assumptions under which it was established. Reuse requires an explicit compatibility check. A capability whose own implementation did not change may depend on a changed component or configuration. Missing change-impact information means reuse is unestablished.

Keep validity axes independent. Invalidating runtime evidence sets that evidence to stale; it must not automatically confer `semantics_reviewed`. If a capability's contract changes, semantic review may also become stale. Retain old results as historical evidence and bind fresh readiness to the current inputs.

## A4 — Derive change impact and distinguish historical references

Add an explicit decision revision, decision status and approval reference. Keep decision versions immutable; derive forward `superseded_by` links from the version history or a separate index. Publishing a draft alternative should not itself revoke an approved decision.

Derive affected records from reverse decision references and relevant dependency relationships, then check the author's `affected_records` list against that result. Otherwise an omitted entry escapes review. Carry invalidation to affected briefs, acceptance cases and evidence; retain their previous versions.

Distinguish current planning decisions from historical business-policy references. Current readiness cannot rely on a superseded decision without review, but an old bill may intentionally retain the superseded tax or payer policy used when it was issued. Effective date and the pinned planning baseline must make that distinction explicit.

## A5 — Define the edge types that propagate priority

Do not traverse every typed reference. Declare a direction and a whitelist of mandatory dependency types: required contract, required capability, required authoritative input, required recovery mechanism and required verification obligation, for example. Provenance, optional consumers, descriptive coupling and historical references do not automatically propagate priority.

Traverse mandatory dependencies through all relevant record types, including invariants and authority obligations; the list of operation/contract/timer/boundary records must not accidentally exclude them. On a graph with cycles, propagate to a fixed point with visited-state tracking. Recompute effective priority from authored priorities when dependencies change so removed prerequisites do not leave stale inherited priority.

## A6 — Measure guesses without authorizing them

Retain `invented_decision` for choices actually made. Add a status distinguishing proposed, blocked, approved and implemented, plus the resolution/decision reference. An unresolved behavioral or contractual choice should first produce a gap finding and the applicable gate; logging it does not authorize an implementer to choose anyway. Ordinary implementation choices within a fully specified contract remain permitted.

Normalize comparisons by the same implemented acceptance scope, foundation revision and task budget. Separate new behavioral gaps, already-declared open decisions and harmless implementation latitude. Deduplicate shared gaps across tickets. Independently sample implementation and contract changes because self-report counts can understate invention. A lower count is useful only if coverage and completion have not fallen.

## Concrete negative fixtures to add to the proposed implementation increment

| Fixture | Expected finding |
|---|---|
| P0 exemption has an approval label but no valid approval reference | A1 gate remains open. |
| Non-exclusive bill finalizations omit their shared numbering race | Missing concurrency obligation; non-exclusivity is not an exemption. |
| Event is covered for one of two receiving machines only | Incomplete receiver coverage. |
| Capability unchanged directly, but a relevant dependency or configuration changed | Reuse cannot remain verified without compatible evidence. |
| Runtime evidence is invalidated on a record never semantically approved | No automatic promotion to semantics reviewed. |
| Decision's authored impact list omits a record that references it | Derived impact detects the omission and invalidates affected readiness. |
| A historical bill references the policy valid when it was issued | Historical reference remains valid; current readiness is checked separately. |
| P0 record has a descriptive reference to an optional P2 consumer | No priority propagation along that reference. |
| Worker logs an unapproved contractual invention and claims completion | Logging does not satisfy the unresolved decision gate. |

These are proposed fixtures, not executed tests. No change to the baseline ticket graph or Python compiler is claimed.
