# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_11: _render_implement uses any-step timing mark for Step 5 window fallback
- **Reviewer(s)**: dyn-progress-gantt-output.txt
- **Severity**: important
- **Concern**: `python/progress_report.py:633-650` — `_render_implement` passes `start_s` from `_latest_timing_mark()` into `_render_step5()` as the in-flight window fallback, but that helper returns the newest any-step mark, not a Step 5-specific mark. On the stale-artifact path (lines 645–650), when the latest mark is still from an earlier step, `_round_dir_is_fresh()` can still route into Step 5 progress. If `round-start-s` is missing (documented on some Step 5 terminal arms), `_render_inflight_gantt()` falls back to that non–Step 5 timestamp and can clip or mis-window reviewer bars relative to the plan’s “Step 5 timing mark” contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-progress-gantt-output.txt: add a helper that selects the latest `mark` row whose step label matches Step 5 (same pattern for design Step 3 in `_render_design`), pass that into `_render_step5` / `_render_design_plan_review`, and keep `_latest_timing_mark()` only for generic elapsed text.


