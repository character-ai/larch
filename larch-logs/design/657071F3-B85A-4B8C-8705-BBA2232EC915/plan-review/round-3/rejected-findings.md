### [Plan Review] FINDING_2

### FINDING_2: Recovery waterfall `continue` paths skip CI stderr-tail surfacing
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: In `ship-pr.sh` recovery waterfall (~2745–2802), several `continue` paths run after a tier launcher can leave `${output}.stderr-tail` populated while `tier_rc=0` (e.g. detached-HEAD ~2754–2756, verify failure ~2800–2802). Surfacing tied only to `tier_rc -ne 0` drops agent stderr tails on those paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one shared post-launcher gate (parse `LAUNCHER_EXIT` from captured stdout when the launcher ran; then `_surface_ci_stderr_tail "$output"` when `tier_rc -ne 0`, `LAUNCHER_EXIT -ne 0`, or `[[ -s "${output}.stderr-tail" ]]`) and call it before every `recovery_waterfall_paths_delta_revert` / `continue` in the tier loop, not only before the `tier_rc -ne 0` branch.


### [Plan Review] FINDING_3

### FINDING_3: SIMPLE-tier scope creep beyond stated implement-launcher gaps
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The plan expands beyond the feature description (Gap 1: implement launchers only, ~30–50 LOC) into three additional lanes—CI fix-loop + recovery waterfall in `ship-pr.sh`, producer+KV in `lint-fix-loop.sh`, parse+surface in `review-implement-step5-loop.sh`—with a much larger diff (~285 lines) and extra test/doc surface. That increases review and regression risk relative to the stated scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Keep this PR to the two stated gaps: (a) launch-codex-implement.sh producer write + step2-implement.sh emit_bailed consumer emit; (b) test-plan-review-loop.sh FD-2 tail test. Extract ship-pr / lint-fix-loop / review-implement-step5-loop changes to a separate follow-up issue with its own plan and LOC estimate

