Laravel 12 · API first · Pest tests. Configure the production database explicitly.

Modules live under app/Modules/<Module>/. One application action per file.
Authorisation belongs at the action boundary, never only in a screen.
Controllers delegate business operations to actions and wrap their responses.
Every declared state transition goes through its state machine.
Read runtime defaults through App\Support\ProvisionalConfig; never bypass a blocked key.
Time-dependent behavior uses a freezable clock. Tests use fakes and never sleep or call remote services.
Background work is idempotent: repeating a job must not duplicate its effect.
A frozen contract change requires separate review. A feature ticket cannot change it.
Surface work, brand/design-system and MCP generation are outside version 0.1.
