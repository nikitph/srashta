---
name: design-system-bootstrap
description: Turn brand.yaml into the frozen design-system contract C-00 of phase 0 — tokens, patterns, DESIGN.md, CI enforcement, evidence page.
---
# Design System Bootstrap
Consumes `brand.yaml`. Produces the design system as **contract `C-00` of phase 0** — frozen alongside the schema, because every UI ticket depends on it as every data ticket depends on the schema. This skill *translates* brand decisions; it does not make them. No `brand.yaml` → run `/brand-identity` first.

**Tokens.** All shadcn semantic vars in both `:root` and `.dark`, plus `success`/`warning`/`info` and their foregrounds. Each added colour also needs a `@theme inline` mapping or its utilities will not exist. Derive from OKLCH: neutrals from `colour.neutral` at chroma 0.005–0.012; primary at L≈0.52 light / 0.70 dark; status hues **fixed across projects** so meaning is stable (destructive 27, warning 75, success 150, info 240); charts categorical = 5 hues at ~72° spacing, sequential = brand hue stepping L 0.85→0.45. Density changes component defaults only, never Tailwind's global spacing.

**Contrast checks are a hard gate**, both modes: ≥4.5 for every foreground on its surface, ≥3.0 for ring, primary and each chart colour on background. Auto-nudge L in 0.01 steps up to 0.15, report every nudge, then stop and name the failing pair. Derived palettes are where contrast bugs hide.

**CI check is what actually stops drift** over long autonomous runs — reject raw hex, palette utilities, arbitrary colours and inline styles outside `components/ui`. DESIGN.md alone will not.

**Evidence page** `/_design` (local and staging only): every token as a swatch with its contrast ratio, type scale, radius samples, every component state, every pattern, charts, status badges. Playwright captures light and dark. **This is the human review gate** — one page, the only design surface to look at per project.

**Patterns**: PageShell, DataTable, FormSection, StatCard, EmptyState, ErrorState, LoadingState, ConfirmDialog, StatusBadge. All on `/_design`.

Register as `C-00` owning `resources/css/app.css`, `design/**`, `components/patterns/**`, `DESIGN.md` and the check scripts. Every UI ticket lists it in `contracts_used`. After the freeze, a change is a contract-change ticket, not an edit — say so plainly rather than quietly regenerating.
