## Proposed Design Outline

### Goals
- Ensure plan revision bars appear in Gantt when `postplan-failed` terminates a round early.
- Show an in-flight timing Gantt in the progress report while reviewers are running.
- Improve Gantt bar labels for aggregator, scout, and plan revision entries.

### Non-goals
- Not changing the Gantt window calculation for normal completion paths (they already work).
- Not adding non-vendor events (tally, continuation) to the Gantt.
- Not changing the table section of Review Phase Detail.

### Approach sketch
- Fix `review-design-step3-loop.sh`: call `step3_loop_record_timing` BEFORE the `postplan-failed` exit in `awaiting-continuation`, `awaiting-post-apply`, and `awaiting-postplan-operator` branches.
- Fix label derivation in `render-review-phase-detail.sh` (derive.awk) and `progress_report.py` (`_derive_progress_label`): special-case "aggregator", "scout-plan-manifest*", and bare vendor-name cores.
- Fix `plan_quality.py` (`revise_plan_with_waterfall_main`): pass `--timing-task-kind codex-plan-autofix` / `cursor-plan-autofix` so revision bars get clear labels.
- Add `_render_inflight_gantt` to `progress_report.py` that renders completed vendor rows without requiring `round-meta.json`; wire into `_render_design_plan_review` and `_render_step5` for in-flight display.

### Surfaces in scope
- `skills/design/scripts/review-design-step3-loop.sh`
- `scripts/render-review-phase-detail.sh` (derive.awk, label_for)
- `python/progress_report.py`
- `python/plan_quality.py` (revise_plan_with_waterfall_main)
- `python/test_progress_report.py` and `scripts/test-render-review-phase-detail.sh` (harness coverage)

### Open questions
- None.
