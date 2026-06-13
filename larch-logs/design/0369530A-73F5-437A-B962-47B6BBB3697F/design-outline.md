## Proposed Design Outline

### Goals
- Fix the `.cap-hit` stale-marker bug in `python/plan_scout.py` so Cursor cap-hits do not silently block a Claude fallback.
- Close five test-coverage gaps: diff-mode dynamic scout, scope-anchor boundary cases, Cursor same-path Step 2 dispatch, and Python-side ship-pr `resolve_launcher_exit` coverage.
- Verify (and if needed patch) the Python ship-pr port's `resolve_launcher_exit` behavior; no bash-side changes.

### Non-goals
- No changes to `scripts/ship-pr.sh` or `scripts/test-ship-pr-rebase.sh` (bash path is being retired).
- No new user-visible behavior or flag changes; this is a bug fix + test-coverage pass.
- No refactoring of unrelated plan_scout paths.

### Approach sketch
- `python/plan_scout.py`: unlink `Path(str(raw) + ".cap-hit")` before each tier launch (Cursor block and Claude block).
- `python/test_plan_scout.py`: add three new test functions covering diff-mode happy path, JSON salvage, and over-cap (max_archetypes=0 / cursor-cap + Claude fallback).
- `python/test_rendering.py`: add four scope-anchor boundary assertions (symlink, zero-byte, >65536-byte, CR/LF-in-path) against `_scope_anchor_common_shape_ok` guards.
- `skills/implement/scripts/test-step2-dispatch.sh`: add Test 13a-scout-cursor variant with a Cursor stub that writes `scout-coder-manifest.json` at the same path.
- `python/agents.py` (or equivalent): confirm `resolve_launcher_exit` fails closed on non-zero wrapper exit; add or strengthen existing test.

### Surfaces in scope
- `python/plan_scout.py`
- `python/test_plan_scout.py`
- `python/test_rendering.py`
- `skills/implement/scripts/test-step2-dispatch.sh`
- `python/agents.py` (read-only verify; patch only if fail-closed semantics are missing)

### Open questions
- None.
