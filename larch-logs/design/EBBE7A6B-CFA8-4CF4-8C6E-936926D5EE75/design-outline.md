## Proposed Design Outline

### Goals
- Add `nofollow=True` to `run_logs._atomic_write` and `tokens._atomic_text` so all state writers share the symlink-guard protection.
- Replace `rmtree(dest) + rename(src, dest)` with `rename(dest, backup) + rename(src, dest) + rmtree(backup)` in both publish paths.
- Narrow `suppress(Exception)` around commit/manifest IO in `run_logs.py` to specific exceptions and add a `print(..., file=sys.stderr)` on catch.

### Non-goals
- Do not harden other `larch_io.atomic_write` callers (clarify, rendering, plan_review, etc.).
- Do not touch `suppress(Exception)` in research, ship, agents, or other non-state modules.
- Do not change the fail-closed secret-scrub or symlink-escape guard paths.
- Do not narrow the `BaseException` seam in `review_and_fix.py`.

### Approach sketch
- Edit `run_logs.py:291` (`_atomic_write`): add `nofollow=True`.
- Edit `tokens.py:1400` (`_atomic_text`): add `nofollow=True`.
- Edit `run_logs.py` publish paths (two sites): swap `rmtree + rename` for `rename-old + rename-new + cleanup-old`.
- Edit three `suppress(Exception)` blocks in `run_logs.py` (lines ~1874, ~1884, ~2207): replace with `try/except (OSError, ...)` that prints a warning on catch.
- Run `make py-test py-lint` to verify.

### Surfaces in scope
- `python/run_logs.py`
- `python/tokens.py`

### Open questions
- None.
