---
name: brand-identity
description: Settle this project's brand into brand.yaml — positioning, adjectives, colour, typography with script coverage, voice, form — so the design system and marketing read one source.
---
# Brand Identity
Schema: `schemas/brand.schema.json`. Runs alongside the back half of spec authoring — it needs positioning, audience and personas only. Must be complete before the design system freezes.

**Decide, don't survey.** Bring options only where the choice is genuinely the person's — brand hue, fonts, register. Four questions is a session; twelve is an interrogation.

**Adjectives matter more than they look** — they are what an agent extrapolates from on a screen nobody specified. "Modern", "clean", "professional" generate nothing. Pick ones that would make a designer choose differently: "unhurried", "precise", "unceremonious".

**Verify script coverage.** `typography.scripts` must list every script the UI renders, and the fonts must actually cover them. For Devanagari or Tamil, check the font — do not assume. A missing script found after the design system freezes is a contract-change ticket.

**Work from adjectives and audience, not a mood board.** Data-dense long sessions → lower chroma, cooler neutral, tighter density; saturation that reads confident for five minutes fatigues over five hours. Trust-carrying products → restraint reads as competence. One typeface with real range beats a pairing chosen for contrast.

Existing brand: extract rather than invent, and mark what was inherited versus chosen.

Checks before writing: fonts cover every script; every adjective would change a decision; density matches the audience not the founder; voice examples are real sentences from this product. Then write `brand.yaml` and say in three lines what you decided and why. The file is the deliverable, not a brand document.
