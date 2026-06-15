## Proposed Design Outline

### Goals
- Fix 5 latent robustness gaps in ship/rebase/research/timing/progress surfaces.
- Ensure CI task kinds `codex-ci`, `cursor-ci`, `claude-ci` are recognized in timing and live Gantt filtering.
- Add focused regression tests for each fix.

### Non-goals
- No changes to merge retry logic beyond MAIN_ADVANCED routing.
- No changes to `scripts/ship-pr.sh` or any bash ship path.
- No new public APIs or abstractions beyond the private helper for Gantt filtering.

### Approach sketch
- `python/ship.py`: add explicit MAIN_ADVANCED branch before CI_NOT_READY; route through existing rebase machinery.
- `python/rebase.py`: pre-clear `${output}.token-record` and pass `allow_output_fallback=True` for codex/cursor conflict-fix launchers.
- `skills/research/references/research-phase.md`: replace both `if ! cmd; then rc=$?` blocks with `rc=0; cmd || rc=$?` pattern.
- `python/timing.py`: add `codex-ci`, `cursor-ci`, `claude-ci` to `TIMING_TASK_KINDS_ALLOWED`.
- `python/progress_report.py`: add `_is_ci_gantt_row(kind, output)` helper and `skip_ci=True` to `_render_inflight_gantt` call.

### Surfaces in scope
- `python/ship.py`, `python/test_ship.py`
- `python/rebase.py`, `python/test_rebase.py`
- `skills/research/references/research-phase.md`
- `python/timing.py`, `python/test_timing.py`
- `python/progress_report.py`, `python/test_progress_report.py`

### Open questions
- None.
