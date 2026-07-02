## Proposed Design Outline

### Goals
- Remove the dead `implement step-0-bootstrap` CLI entry point (`step0_bootstrap_main`) and its exclusive helpers.
- Deregister it from `cli.py`'s dispatch table and `implement_dispatch.py`'s re-export.
- Keep the sibling `step0_degraded_gate_main` (documented, intentionally-retained) fully intact.

### Non-goals
- Do not touch `skills/implement/scripts/step-0-bootstrap.sh` or port it to Python (explicitly rejected by the earlier "C4a" sh-to-py design decision).
- Do not change `bootstrap invoke` / `larch.state.bootstrap` behavior.
- Do not add new test coverage for the deleted function; there is nothing left to cover once it is gone.

### Approach sketch
- Delete `step0_bootstrap_main`, `_build_step0_bootstrap_parser`, `_Step0BootstrapFields`, `_step0_bootstrap_resume_fields`, `_step0_bootstrap_fork_upstream` from `python/larch/implement/dispatch_bootstrap.py`; prune imports that become unused as a result.
- Remove the `("implement", "step-0-bootstrap")` line from the `_REGISTRY` table in `python/larch/cli.py`.
- Remove `step0_bootstrap_main` from the `implement_dispatch.py` re-export block; keep `step0_degraded_gate_main`.
- Regenerate `python/env-via-config-constant-baseline.json` via `make regen-env-via-config-constant-baseline` to drop the now-stale grandfathered entries for the deleted function.

### Surfaces in scope
- `python/larch/implement/dispatch_bootstrap.py`
- `python/larch/cli.py`
- `python/larch/implement/implement_dispatch.py`
- `python/env-via-config-constant-baseline.json`

### Open questions
- None.
