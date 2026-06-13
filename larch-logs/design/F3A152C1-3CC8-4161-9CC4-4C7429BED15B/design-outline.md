## Proposed Design Outline

### Goals
- Fix the progress report hook to show ship-pr phase when ship-pr is running, regardless of which specific phase string is active.
- Eliminate the `SHIP_PR_PHASES` allowlist that silently falls through to generic output for unrecognized phases.

### Non-goals
- Changing what `_render_ship_pr` displays.
- Fixing any bash ship-pr or Python ship.py phase-naming conventions.
- Adding new fields to the ship-pr state output.

### Approach sketch
- Remove `SHIP_PR_PHASES` frozenset from `progress_report.py` (unused after fix).
- In `_render_implement`, change the ship-pr detection from `is_file() and phase in SHIP_PR_PHASES` to just `is_file()`.
- Keep the `phase = _kv_value(...)` read for the downstream `not phase` guard in the step5 fallback.
- Add a test covering a phase not in the old allowlist (e.g., `bump`).

### Surfaces in scope
- `python/progress_report.py`
- `python/test_progress_report.py`

### Open questions
- None.
