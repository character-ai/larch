# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Prune-empty convergence bypasses Step 3 terminal sentinels and complete envelope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-dyn-review-convergence-output.txt
- **Severity**: blocking
- **Concern**: After #5255, a round 3 or 4 prune-to-empty panel sets `PLAN_REVIEW_CONTINUE=false` with reason `converged-pruned-empty`, then `run_step3_review` exits via the `degraded_exit` branch (lines 2354-2372). That branch only emits stdout KVs (`LOOP_STATUS=zero-findings-degraded-panel`, round provenance) and returns. It does not call `step3_loop_write_completed_step3()`, `step3_loop_persist_envelope()`, or `step3_loop_emit_envelope()` like the normal complete path at 2373-2380. It also does not merge continuation KVs (including `PLAN_REVIEW_CONTINUE_REASON=converged-pruned-empty`) into the durable envelope. Result: `.completed/step-3`, `.completed/step-3.5`, `.completed/step-3-terminal`, and `.step3-terminal-persisted-this-run` are never written; `STEP3_REVIEW_LOOP_STATUS=complete` is absent. `/design` Step 3 background wait blocks on missing `step-3-terminal`; `design-step3-review.sh` guarantee trap cannot backfill because `STEP3_REVIEW_LOOP_STATUS` is not in the allowed terminal set. Round provenance in stdout may be preserved (#5194), but the orchestrator cannot advance to Step 3b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reuse the complete branch terminalization: merge cont into complete_values, call step3_loop_write_completed_step3 and step3_loop_emit_envelope(..., "complete", ...).
  - From cursor-specialist-correctness-output.txt: Merge cont KVs (including PLAN_REVIEW_CONTINUE_REASON) in the shared terminal-finalization path.
  - From codex-specialist-correctness-output.txt: In the `degraded_exit` branch, persist the terminal envelope and write the same Step 3 sentinels as the complete path, while preserving `LOOP_STATUS=zero-findings-degraded-panel` and the nonzero round provenance.
  - From cursor-specialist-edge-cases-output.txt: Mirror the complete branch on converged-pruned-empty: merge continuation KVs call step3_loop_write_completed_step3 then step3_loop_emit_envelope with status complete so persist writes terminal sentinels and STEP3_REVIEW_LOOP_STATUS
  - From codex-specialist-edge-cases-output.txt: Mirror the normal complete path for this terminal convergence case: merge the continuation reason into the carry values, call the Step 3 completion writer, and persist a terminal envelope via `step3_loop_persist_envelope()` / `step3_loop_emit_envelope()` so the terminal sentinel pair is written before returning.
  - From cursor-specialist-testing-output.txt: Mirror the complete branch: write completed step-3 call step3_loop_emit_envelope with complete status and converged-pruned-empty reason or explicitly persist plus step3_loop_write_terminal_step3.
  - From codex-specialist-testing-output.txt: Route `converged-pruned-empty` through the same terminal-complete persistence path as `complete`, or explicitly write the completed sentinels plus `step3_loop_persist_envelope()` / `step3_loop_write_terminal_step3()` before returning.
  - From dyn-dyn-review-convergence-output.txt: On prune-empty stop (`degraded_exit` and `PLAN_REVIEW_CONTINUE_REASON=converged-pruned-empty`), mirror the `complete` branch: merge continuation KVs into `complete_values`, call `step3_loop_write_completed_step3(tmpdir)`, then `step3_loop_emit_envelope(tmpdir, "complete", round_num, round_num, round_num, complete_values)` with `LOOP_STATUS=complete` (or an explicit `STEP3_REVIEW_LOOP_STATUS=complete`) so the terminal-loop matrix skips Gate B.


