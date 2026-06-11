## Proposed Design Outline

### Goals
- Show plan-review round details (round number, reviewer counts, elapsed time) in the `/design` progress report when in Step 3
- Reuse existing `_current_round_dir`, `_returned_reviewers`, `_round_elapsed` helpers; extract the script-call logic from `_render_review_detail` into a shared helper so the design path doesn't duplicate it
- Add tests covering the new design plan-review rendering path

### Non-goals
- Progress detail for design steps other than Step 3 / 3.5 / 3b (Step 2a sketches, Step 5 finalize, etc. keep the generic report)
- Changes to `hook-progress-report.sh` or `render-review-phase-detail.sh`
- Ship-PR analog for design (no equivalent phase)

### Approach sketch
- Extract `_call_render_phase_detail_script(rounds_root, skill, timing_ledger, token_ledger)` from the body of `_render_review_detail` to share the script invocation logic
- Refactor `_render_review_detail` to delegate to the new helper (no signature change, existing tests unaffected)
- Add `_render_design_review_detail(design_tmpdir)` — calls helper with `rounds_root=design_tmpdir/"plan-review"` and `skill="design"`
- Add `_render_design_plan_review(design_tmpdir)` — mirrors `_render_step5` using the `plan-review/round-N/` directory structure
- Update `_render_design(run)` to detect `"Step 3" in step_label` and try `_render_design_plan_review` before falling back to generic

### Surfaces in scope
- `python/progress_report.py`
- `python/test_progress_report.py`

### Open questions
- None.
