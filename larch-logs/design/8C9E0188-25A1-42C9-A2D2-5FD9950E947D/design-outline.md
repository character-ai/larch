## Proposed Design Outline

### Goals
- Create `python/tests/support/session.py` with `make_implement_tmpdir`, `make_design_tmpdir`, `write_session_env`, and seed helpers for plan.txt/feature-description.txt/run-params.json.
- Re-export all builders through `python/test_support.py` (flat) so every test uses a consistent import path.
- Migrate 6 files (`test_implement_dispatch.py`, `test_session_env.py`, `test_bootstrap.py`, `test_closeout.py`, `test_final_report.py`) to use the shared builders, removing inline `_session()` duplication and scattered session-env writes.

### Non-goals
- Migrating local `CLI` / `run_cli` duplicates (covered by other pieces).
- Adding new flat `python/test_*.py` files at the repo root.
- Changing production session_env key contracts.

### Approach sketch
- Add `python/tests/__init__.py` (empty) so `tests.support.session` is importable from `test_support.py`.
- Write `session.py` with a canonical baseline (`CURSOR_PRESENT=false`, `CODEX_BINARY_FOUND=true`, `CURSOR_BINARY_FOUND=true`, `LARCH_CLAUDE_PLUGIN_ROOT`, `REPO_ROOT`) derived from `_session()` in dispatch tests; support keyword overrides.
- Update `test_support.py` to import and re-export `make_implement_tmpdir`, `make_design_tmpdir`, `write_session_env`.
- Migrate dispatch tests: replace all 192 `_session(tmp_path)` calls with `make_implement_tmpdir(tmp_path)`.
- Migrate state/report tests: replace inline `session-env.sh` setup writes with `write_session_env` or builder helpers where the canonical baseline applies.

### Surfaces in scope
- `python/tests/support/session.py` (new)
- `python/tests/__init__.py` (new, empty)
- `python/test_support.py` (updated: add re-exports)
- `python/tests/implement/test_implement_dispatch.py`
- `python/tests/state/test_session_env.py`
- `python/tests/state/test_bootstrap.py`
- `python/tests/state/test_closeout.py`
- `python/tests/report/test_final_report.py`

### Open questions
- None.
