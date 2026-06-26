## Proposed Design Outline

### Goals
- Fix `_render_implement` in `progress_report.py` so step-mark checks take priority over `ship-pr-state.sh`.
- Ensure that after stall recovery re-enters Step 5, the progress report shows the Step 5 view, not the stale ship-pr view.

### Non-goals
- Not clearing `ship-pr-state.sh` during stall recovery.
- Not changing ship-pr rendering when the run is actually in the ship-pr phase.
- Not modifying stall recovery logic or any script outside `progress_report.py` and its test file.

### Approach sketch
- In `_render_implement`, move the `if (tmpdir / "ship-pr-state.sh").is_file(): return _render_ship_pr(tmpdir)` check to after the step-mark / fresh-round-dirs checks.
- The reordered logic: (1) if done marker exists, skip to ship-pr or generic; (2) if "Step 5" in step_label, try Step 5 render; (3) if stale marks but fresh round dirs, try Step 5 render with note; (4) otherwise try ship-pr-state.sh; (5) fall through to generic.
- Add a regression test for the stall-recovery scenario: ship-pr-state.sh exists with PHASE=checks but latest step mark says "Step 5 — code review".

### Surfaces in scope
- `python/progress_report.py` (function `_render_implement`, lines ~1465–1485)
- `python/test_progress_report.py` (one new test)

### Open questions
- None.
