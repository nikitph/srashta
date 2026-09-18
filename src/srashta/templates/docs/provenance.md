# Where this comes from

Most of this method is assembled from established practice. Recording the mapping so that when
something breaks, the mature literature can be consulted rather than the failure re-derived.

| Element here | Established as |
|---|---|
| Total coverage, one owner per requirement | WBS 100% rule + mutual exclusivity (PMI) |
| Frozen contracts enabling parallel work | **Design rules** — Baldwin & Clark, *Design Rules: The Power of Modularity* (2000) |
| Modules, cross-module flows | Information hiding (Parnas 1972); bounded contexts and context maps (Evans, DDD) |
| Dependency-derived waves | Topological layering; Parnas's "uses" hierarchy for working subsets |
| Requirement → ticket → test links | Requirements traceability matrix; ISO/IEC/IEEE 29148:2018; DO-178C |
| Acceptance criteria | EARS — Mavin et al. (2009); *Specification by Example* (Adzic) |
| Requirement quality characteristics | ISO/IEC/IEEE 29148:2018 §5.2 |
| Transition tables tested both ways | Model-based testing: transition tour + sneak-path coverage |
| Decisions with rejected alternatives | Architecture Decision Records (Nygard, 2011) |
| Interfaces with in-memory fakes | Ports and adapters (Cockburn); test doubles (Meszaros, *xUnit Test Patterns*) |
| Spec defect detection | Requirements smells — Femmer et al., *Journal of Systems and Software* (2016) |
| Defaulting open questions to keep moving | Set-based concurrent engineering (Ward/Toyota); last responsible moment |
| Dependency structure matrix | Steward (1981); Baldwin & Clark (2000); Eppinger & Browning (2012) |

## What the literature does not cover

It assumes a human consumer who can be trusted to consult a large document and ignore the
irrelevant parts. Two adaptations follow from the consumer being an agent instead:

**Bounded context packs.** Information hiding applied to the context window. The agent receives its
pack and nothing else. Every established frame here would happily hand an engineer the whole spec.

**Granularity calibration.** INVEST and story-point conventions encode what is tractable for a
human team. The equivalent for "one autonomous agent run, one pull request" is unmeasured. Step 7
measures it.

Expect the established frames to supply good vocabulary and checklists, and to under-constrain in
exactly the places agents fail — which is why the rules that matter are machine-checked rather
than written down.
