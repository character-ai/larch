## Goal
Implement issue #5169: [IMPLEMENTING] [py-code-quality] Packaging 3/9: move session/lifecycle state into larch.state.

## Implementation Plan
**Problem.** Session, admission, and run-lifecycle state modules are flat with no package boundary, despite forming a coherent subsystem. `session_env` has 9 importers; the lifecycle helpers are coupled.

**Proposed change.** Move the state subsystem into `larch.state`: `session_env`, `dirty_tree`, `bootstrap`, `admission`, `finalize`, `closeout`, `stall_recovery`. Rewrite all importers to `from larch.state import ...`. Update the `cli.py` `_REGISTRY` entries for these modules. Exact module set is finalized in this child's `/design`.

**Out of scope / don't-touch.** No behavior change. Keep the invocation contract and all wire formats (`.sh` env-file format, state KV grammar). Pure move plus import rewrites.

**Acceptance.** State modules live under `larch.state`; importers and registry repointed; `make py-lint` / `make py-test` green; consumer invocations unchanged.

**Effort / risk.** Medium / medium.

**Dependencies.** Blocked by the foundation packaging child (1/9). Tracked under umbrella #4982. Wired via `/block-issue`.

## Test plan
(no test plan section in plan-file)
