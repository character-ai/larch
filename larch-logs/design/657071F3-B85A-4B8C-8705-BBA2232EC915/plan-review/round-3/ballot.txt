Normalizing the five reviewer inputs into a merged finding list per the aggregator rules.
### FINDING_1: Model-args failure never writes `.stderr-tail` before early exit
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic, unknown-slot
- **Severity**: important
- **Concern**: On `agent-model-args.sh` failure, `launch-codex-implement.sh` appends to `$SIDECAR_LOG` and exits with `LAUNCHER_EXIT` before the auth-retry loop and the post-loop `write_failed_agent_stderr_tail` block (~347). `${TRANSCRIPT_PATH}.stderr-tail` is never produced, so step2 `emit_bailed` / `emit_failed_agent_stderr_tail_larch_err` no-ops despite actionable sidecar content. The same early-exit pattern exists in `launch-cursor-implement.sh` (~237–248), where `run-external-agent` auto-write never runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true on the MODEL_ARGS_RC exit path (same as post-loop failure block)
  - From Cursor-Pragmatic: Also call `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` on the model-args failure path before its `exit 0`, or extract a small shared helper invoked from every non-success launcher exit that has sidecar content.
  - From unknown-slot: Add `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` inside the `if [[ "$MODEL_ARGS_RC" -ne 0 ]]; then` branch (around line 295, after the `cat "$MODEL_ARGS_ERR" >> "$SIDECAR_LOG"` line) in addition to the post-retry-loop placement. Same fix applies to the analogous model-args failure branch in `scripts/launch-cursor-implement.sh:237-248` — that path also exits before run-external-agent is called, so the auto-write by `run-external-agent` cannot fire.

### FINDING_2: Recovery waterfall `continue` paths skip CI stderr-tail surfacing
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: In `ship-pr.sh` recovery waterfall (~2745–2802), several `continue` paths run after a tier launcher can leave `${output}.stderr-tail` populated while `tier_rc=0` (e.g. detached-HEAD ~2754–2756, verify failure ~2800–2802). Surfacing tied only to `tier_rc -ne 0` drops agent stderr tails on those paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one shared post-launcher gate (parse `LAUNCHER_EXIT` from captured stdout when the launcher ran; then `_surface_ci_stderr_tail "$output"` when `tier_rc -ne 0`, `LAUNCHER_EXIT -ne 0`, or `[[ -s "${output}.stderr-tail" ]]`) and call it before every `recovery_waterfall_paths_delta_revert` / `continue` in the tier loop, not only before the `tier_rc -ne 0` branch.

### FINDING_3: SIMPLE-tier scope creep beyond stated implement-launcher gaps
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The plan expands beyond the feature description (Gap 1: implement launchers only, ~30–50 LOC) into three additional lanes—CI fix-loop + recovery waterfall in `ship-pr.sh`, producer+KV in `lint-fix-loop.sh`, parse+surface in `review-implement-step5-loop.sh`—with a much larger diff (~285 lines) and extra test/doc surface. That increases review and regression risk relative to the stated scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Keep this PR to the two stated gaps: (a) launch-codex-implement.sh producer write + step2-implement.sh emit_bailed consumer emit; (b) test-plan-review-loop.sh FD-2 tail test. Extract ship-pr / lint-fix-loop / review-implement-step5-loop changes to a separate follow-up issue with its own plan and LOC estimate
