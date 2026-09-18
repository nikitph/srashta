<!-- The invariant rules every ticket inherits. Lives in the blueprint, not the project.
     Replace the stack lines for a different stack; the discipline lines carry over. -->
Laravel 12 · Inertia · React · shadcn/ui · Pest · Postgres.

Modules live under app/Modules/<Module>/. One application action per file.
Authorisation is a policy at the action layer, never only in the interface.

**No controller contains business logic.** A controller method calls one action and wraps
the response - a JSON resource in the API controller, an Inertia render in the web one.
Both call the SAME action. This is what makes the two surfaces provably equivalent rather
than merely parallel, and it is checked in CI.
Every state transition goes through its state machine, never a direct attribute write.
Colours come from semantic design tokens only; CI rejects raw hex and palette utilities.
Spacing comes from the scale; no arbitrary values.
Tests are Pest. Time is read through the Clock interface, never sleep().
Background work is idempotent: a job that runs twice produces no duplicate effect.
Every screen needs loading, empty and error states from the pattern library.
Need a new token, pattern or contract? Do not invent it inline — file a change ticket.
