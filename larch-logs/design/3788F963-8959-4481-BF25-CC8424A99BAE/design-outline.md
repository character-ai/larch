## Proposed Design Outline

### Goals
- Add a frozen `LauncherPaths` that owns the sidecar file-family, derived once from `output`.
- Extract one shared `_finalize_launch` epilogue for the duplicated record-task -> meta-append -> promote-done -> append-failure -> emit tail.
- Replace open-coded `CODEX_HOME`/`CURSOR_CONFIG_DIR` save/restore with the existing `_temporary_env` context manager.

### Non-goals
- No change to the `KEY=value` stdout or `.done`/`.meta` sidecar IPC contract; sidecar path strings stay byte-identical.
- Do not touch the startup lock, magic exit-code sets, or `USER or "larch"` fallback.
- No argv-grammar or vendor-behavior change; Codex/Cursor parity preserved.

### Approach sketch
- Add `LauncherPaths` (frozen) in `python/agents.py`, mapping each field to its exact existing suffix.
- Migrate only the stable sidecar-family `.with_suffix` sites rooted at each launcher's canonical `output`; leave PID-keyed temps and non-`output`-rooted constructions alone.
- Extract `_finalize_launch(tool, paths, result, ...)`; parametrize per-family tail differences instead of forcing one shape.
- Swap `CODEX_HOME`/`CURSOR_CONFIG_DIR` save/restore to `with _temporary_env(...)`.
- Add focused unit tests; keep launcher-parity / `test_agents.py` green.

### Surfaces in scope
- `python/agents.py` (the refactor).
- `python/test_agents.py` (new unit tests + existing parity coverage).

### Open questions
- Whether `run_external_agent` itself adopts `LauncherPaths`, given its env-overridable `.done` suffix. Resolve in Step 2b.
- Exact `_finalize_launch` parameter set spanning the CI / review / implement / drafter tails. Resolve in Step 2b.
