### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-implement.sh:290-300
- **Concern**: Producer write only after auth-retry loop; MODEL_ARGS preflight exits early. Scenario: MODEL_ARGS failure fills SIDECAR_LOG but never writes ${TRANSCRIPT_PATH}.stderr-tail; step2 emit_bailed only emits from that file
- **Proposed resolution**: Add write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true on the MODEL_ARGS_RC exit path (same as post-loop failure block)

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2745-2802
- **Concern**: Recovery waterfall has multiple `continue` paths after a tier launcher can exit 0 while still leaving `${output}.stderr-tail`. Scenario: The plan’s ship-pr edit window (~2728–2747) and failure-mode #4 focus on `tier_rc` / `LAUNCHER_EXIT` immediately after the launcher call, but the loop also `continue`s on detached-HEAD (2754–2756) and verify failure (2800–2802) with `tier_rc=0`. Surfacing only in the `tier_rc -ne 0` block drops CI agent tails on those paths.
- **Proposed resolution**: Add one shared post-launcher gate (parse `LAUNCHER_EXIT` from captured stdout when the launcher ran; then `_surface_ci_stderr_tail "$output"` when `tier_rc -ne 0`, `LAUNCHER_EXIT -ne 0`, or `[[ -s "${output}.stderr-tail" ]]`) and call it before every `recovery_waterfall_paths_delta_revert` / `continue` in the tier loop, not only before the `tier_rc -ne 0` branch.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-implement.sh:290-300
- **Concern**: Producer write is only planned inside the post-auth `if (( LAUNCHER_EXIT != 0 ))` block at ~347; the model-args failure path exits at ~300 with SIDECAR_LOG populated but never reaches that block.. Scenario: `agent-model-args.sh` failure is a common implementer failure; step2 `emit_failed_agent_stderr_tail_larch_err "$TRANSCRIPT_PATH"` no-ops because `${TRANSCRIPT_PATH}.stderr-tail` was never written despite actionable text in `$SIDECAR_LOG`.
- **Proposed resolution**: Also call `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` on the model-args failure path before its `exit 0`, or extract a small shared helper invoked from every non-success launcher exit that has sidecar content.

### FINDING_4:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/ship-pr.sh, scripts/lint-fix-loop.sh, skills/review-and-fix/scripts/review-implement-step5-loop.sh, scripts/test-ship-pr.sh, scripts/test-lint-fix-loop.sh, scripts/lint-fix-loop.md, scripts/ship-pr.md
- **Concern**: SIMPLE-tier scope creep: plan adds three out-of-scope lanes (CI fix-loop + recovery waterfall in ship-pr.sh, producer+KV in lint-fix-loop.sh, parse+surface in review-implement-step5-loop.sh) not mentioned in the feature description. Scenario: Feature description Gap 1 names only "implement launchers" (launch-codex-*.sh, launch-cursor-*.sh) with ~30-50 LOC estimate; the plan proposes 285 diff_lines by pulling in ship-pr, lint-fix, and step5 — three lanes the feature explicitly did not request, making the PR significantly harder to review and regress
- **Proposed resolution**: Keep this PR to the two stated gaps: (a) launch-codex-implement.sh producer write + step2-implement.sh emit_bailed consumer emit; (b) test-plan-review-loop.sh FD-2 tail test. Extract ship-pr / lint-fix-loop / review-implement-step5-loop changes to a separate follow-up issue with its own plan and LOC estimate

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/launch-codex-implement.sh:289-300
- **Concern**: Model-args failure early-exit bypasses the proposed producer-write block. Scenario: When `agent-model-args.sh` fails, the script does `cat "$MODEL_ARGS_ERR" >> "$SIDECAR_LOG"` then emits `LAUNCHER_EXIT "$MODEL_ARGS_RC"` and exits 0 at line ~300 — before the auth-retry loop and the `if (( LAUNCHER_EXIT != 0 ))` block (line ~347) where the plan places `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true`. Step2's `emit_bailed` call to `emit_failed_agent_stderr_tail_larch_err "$TRANSCRIPT_PATH"` finds no `.stderr-tail` and silently returns 1.
- **Proposed resolution**: Add `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` inside the `if [[ "$MODEL_ARGS_RC" -ne 0 ]]; then` branch (around line 295, after the `cat "$MODEL_ARGS_ERR" >> "$SIDECAR_LOG"` line) in addition to the post-retry-loop placement. Same fix applies to the analogous model-args failure branch in `scripts/launch-cursor-implement.sh:237-248` — that path also exits before run-external-agent is called, so the auto-write by `run-external-agent` cannot fire.
