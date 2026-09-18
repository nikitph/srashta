---
name: spec-readiness
description: Audit open questions into blockers vs parameters, derive modules, assign every requirement to a phase. Once per project, before any phase is decomposed.
---
# Spec Readiness
Run `srashta run`. It parses, lints, derives modules and assigns phases, and reports decisions rather than mechanics. Your job is the classification it cannot do.

**Blocker vs parameter — the most valuable judgment in this skill.** A *blocker* changes the shape of the system: a different table, a different flow, a different party in the money path, an integration added or removed. Record which phase it gates. A *parameter* changes a value: give it a default in `config/defaults.yaml`, taken from the spec's working assumptions where stated, marked `[derived]` where you chose it.

**Before calling something a blocker, ask whether a modelling decision dissolves it.** A boolean consent flag makes "does purpose X need separate consent?" a blocker; a purpose-scoped consent record makes it a row. Record such decisions — they are high-value and reviewable.

**Hunt coverage gaps deliberately.** A domain the phase plan never names will be orphaned by decomposition. `srashta assign` refuses to run when it finds one, but find them first and report them as spec defects.

**The DSM is an accelerator, not an oracle.** Review the disagreements between clustering and the domain-prefix prior: each is a misfiled requirement or a genuine cross-module flow. High coupling can mean a true flow needing a contract, or a true hub that is universal by nature. You decide which. If it reports low confidence it has already fallen back — no action needed.

**Expect the foundations phase to be the largest.** It holds the universal contracts plus the security, data-protection, accessibility and observability baselines that are cheap now and brutal to retrofit. Say so, because it will look like over-scoping.

Gate: the human answers only the blockers gating the first phase.
