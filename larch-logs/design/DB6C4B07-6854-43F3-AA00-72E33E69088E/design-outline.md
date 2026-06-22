## Proposed Design Outline

### Goals
- Add a read-once typed `Ctx` dataclass; build it once at each `_core` boundary and pass `ctx` down explicitly.
- Adopt `Ctx` at the `_core` boundaries of the 3 hotspots: `agents.py`, `design_lifecycle.py`, `plan_quality.py`.
- Replace cross-step-IPC `os.environ[...] =` writes in `design_lifecycle.py` with explicit `ctx`/return passing.

### Non-goals
- No full per-file `os.environ` read sweep; deep legacy reads keep working.
- Keep entrypoint `os.environ` save/restore in `*_core` and the `.sh` env-file wire format unchanged.
- Do not touch env writes that configure spawned subprocesses (e.g. `CLAUDE_PID`, launcher-inherited vars).

### Approach sketch
- New module `python/ctx.py` with `Ctx` plus `Ctx.from_env()` reading `os.environ` once via existing `config.ENV_*` constants (keeps config.py logic-free).
- Each hotspot `_core` builds `ctx = Ctx.from_env()` at entry; new and refactored helpers take `ctx`.
- In `design_lifecycle.py`, route step-to-step values through `ctx` fields or return values instead of in-process env writes; preserve subprocess-facing writes.
- Add unit tests for `Ctx.from_env()` parsing and defaults.

### Surfaces in scope
- `python/ctx.py` (new), `python/agents.py`, `python/design_lifecycle.py`, `python/plan_quality.py`.
- `python/config.py` (reuse `ENV_*` constants; add new names only if needed).
- `python/test_ctx.py` (new) plus touched hotspot tests.

### Open questions
- Final `Ctx` home and exact field set (new `ctx.py` vs. fold into an existing module) settled in plan drafting.
