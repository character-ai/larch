# Review Round 1

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_2: dispatch_panel omits DYNAMIC_RENDER_PANEL_WARNING when dispatch-waterfall fails
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-dynamic-panel-output.txt
- **Severity**: important
- **Concern**: `dynamic_warning` is emitted on the `PANEL_PRUNED_EMPTY` early return and the post-waterfall success tail, but not when `dispatch-waterfall` exits non-zero. On that path `dispatch_panel` returns before emitting `DYNAMIC_RENDER_PANEL_WARNING`, even when dynamic renders already failed and per-slot warnings were written to `execution-issues.md`. `plan_review_round.py` sets `LOOP_STATUS=panel-failed` without parsing panel KVs on non-zero waterfall exit, so aggregate dynamic-render degradation is invisible on the combined “render failed, then waterfall failed” outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Emit dynamic_warning before waterfall dispatch or inside the waterfall failure branch before returning.
  - From dyn-dynamic-panel-output.txt: Emit `DYNAMIC_RENDER_PANEL_WARNING` on the waterfall-failure exit path as well (before the early `return proc.returncode`), and extend `test_plan_review_panel.py` with a case where dynamic render fails and the waterfall stub exits non-zero, asserting the KV is still present in `panel-dispatch` stdout.


### FINDING_3: Dynamic render warning logging can abort panel dispatch
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If dynamic render fails while `execution-issues.md.lock.d` is stale, `run_logs.append_execution_issue` raises after retries and `_dynamic_slot_rows` aborts before fallback rows and the manifest are written. Panel dispatch can fail entirely instead of degrading gracefully with fallback prompts and an aggregate warning KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Catch OSError around _append_dynamic_render_warning, keep the failure tuple, and continue to emit the aggregate warning KV


