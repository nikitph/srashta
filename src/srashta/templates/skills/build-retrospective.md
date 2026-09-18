---
name: build-retrospective
description: Turn the execution event log into evidence-based corrections to the decomposition, the blueprint and the method. At each phase exit gate.
---
# Build Retrospective
Read `srashta event --summary --phase N` and the log at `events/phase-N.jsonl`. This is what makes ticket size, pack sufficiency and contract quality *measured* rather than argued.

**Ground every finding in the log.** A retrospective reporting impressions is worse than none — it launders guesses into process changes. If a signal is missing, say the question is unanswered and fix the instrumentation before the next phase.

**1 Ticket size.** Plot success against size — acceptance-test count, owned-file count, diff lines. Find where attempts and review rounds rise sharply. If tickets above N criteria need multiple attempts and those below land first time, **N is a hard ceiling**: state it as a number and set `max_acceptance_tests`.

**2 Pack sufficiency.** Every `out_of_scope_touch` is a pack that omitted something or an ownership assignment that was wrong. Read the diff and say which. Recurring omissions of one kind become a standing section in the pack template.

**3 Contract quality.** Every `contract_change_filed` is a contract-design miss. Classify: unforeseeable, or something the design step should have caught? The second kind becomes a checklist item. **Zero changes across a phase is also a finding** — either the contracts were good or so loose they constrained nothing; check whether agents diverged in ways a contract should have prevented.

**4 Acceptance-test quality.** High `first_run_test_failures` may mean ambiguous criteria rather than hard work. A ticket that passed first time but was rejected in review is the more serious defect: the tests did not capture what done meant.

**5 Wave accuracy.** Any ticket that blocked on something its dependencies did not declare is a missing edge. Record the pattern that produced it.

Where several models worked the phase, compare success by ticket kind and state it as a **routing rule**, not a judgment about a model.

Split corrections three ways and keep the lists separate: **this project's next phase**, **the blueprint**, **the method** (a rule that should be machine-checked rather than remembered — propose the validator check). Mixing a project fix into the blueprint is how blueprints rot.

Close the phase with `srashta close N --by NAME` after the retrospective and verified merge evidence are present. A retrospective file alone does not mean execution is complete. Historical evidence lives in evidence/, outside disposable build/.
