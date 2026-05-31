### FINDING_1: code-quality: skills/implement/scripts/step2-implement.sh:1064-1080
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] emit_failed_agent_stderr_tail_larch_err is only called from emit_bailed() not from the final manifest status=bailed envelope Agent returns LAUNCHER_EXIT=0 with manifest status bailed after writing stderr; orchestrator gets SIDECAR_LOG KV but no fenced stderr tail in chat Add emit_failed_agent_stderr_tail_larch_err "$TRANSCRIPT_PATH" || true to the bailed) case arm or share a helper with emit_bailed()
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/test-ship-pr.sh:6316-6362
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] #3227 run_lint_fix_loop_capture tests omit LINT_FIX_STATUS=failed even though ship-pr surfaces on failed. A regression in failed-status tail parsing/emission would not fail make test-ship-pr while Step 5 parser tests still pass. Add a failed-status stub with CODER_LOG_FILE and seeded .stderr-tail; assert caller stderr receives the probe.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/implement/scripts/test-cursor-implementer.sh:899-904
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Cursor agent-failure test does not assert redaction/bounds unlike codex harness. Raw secrets in cursor .stderr-tail could ship to chat without CI catching it. Mirror codex redaction/secret assertions on the cursor failure path.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/ship-pr.sh:150-155
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan empty-with-failure lint_status guard not implemented in run_lint_fix_loop_capture. rc 0 plus empty LINT_FIX_STATUS would skip caller-scope surfacing despite an on-disk tail. Implement empty-status surfacing or prove lint-fix-loop cannot emit it; add a harness case if realistic.
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: skills/design/scripts/plan-review-loop.sh:757-765
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Collector subshell uses `|| true`, dropping `_collect_rc` failure handling added in round 1. Collector exits non-zero with empty/unparseable stdout: stderr tail reaches FD 2, but loop continues without `panel-failed` / empty-review guard. Commit staged `set +e` + `_collect_rc` + parseable-output check; remove bare `|| true`.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: scripts/lint-fix-loop.sh:247-292
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] `_LINT_FIX_STDERR_TAIL_STEM` always overwritten by the last external failure. Codex agent fails with rich stderr, then cursor preflight fails: `STDERR_TAIL_PATH` points at cursor and chat shows preflight noise while `codex.log.stderr-tail` is ignored. Prefer first non-empty tail stem, or set stem only when unset / new tail is richer.
- **Suggested revision**: Address the concern above.


### FINDING_33: architecture: scripts/ship-pr.sh:2752-2773
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Recovery waterfall leaves `launcher_stdout` capture files behind. Long recovery runs accumulate orphaned `recovery-*-launcher-*.out` files under `$IMPLEMENT_TMPDIR`. `rm -f` each `launcher_stdout` after parsing, or reuse one temp path per waterfall.
- **Suggested revision**: Address the concern above.


### FINDING_35: correctness: scripts/ship-pr.sh:150-155
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] run_lint_fix_loop_capture omits plan's empty-with-failure surfacing gate Malformed or truncated lint-fix stdout can yield rc=0 and empty LINT_FIX_STATUS while a stderr-tail artifact exists; _surface_lint_fix_stderr_tail is skipped and chat never shows the tail Also surface when lint_status is empty after a failed capture (e.g. rc!=0, non-empty fail_file, or parseable STDERR_TAIL_PATH/CODER_LOG_FILE fallback)
- **Suggested revision**: Address the concern above.


### FINDING_36: **correctness** `skills/design/scripts/plan-review-loop.sh:757-764` — Round 1 replaced the original `|| _collect_rc=$?` guard (introduced in `3de7ceaaf`) with `|| true`, so the collector’s exit status is no longer captured on HEAD. That does **not** block `_collect_out` assignment on a non-zero collector exit (bash still fills the command substitution from stdout before evaluating the list’s status), and bash waits for the `2> >(tee …)` process substitution to finish before the assignment completes, so the FD-2 / `plan-review-collector.stderr` tail test can pass. The defect is semantic: without `_collect_rc`, the driver cannot tell a hard collector failure (empty/unparseable stdout) from a partial success, so it keeps going into manifest/slot/voter/tally work and multi-round callers can end in `degraded-empty-collector` instead of an early `panel-failed` round failure. **`|| true` is also redundant for `set -e` abort avoidance here**, because both call sites of `_run_plan_review_round` already run it under `set +e` (`1222-1225`, `1260-1263`). **Suggested fix:** Drop `|| true` and restore explicit status handling—the uncommitted working-tree pattern is the right shape: `set +e` around the collect assignment, `_collect_rc=$?` immediately after (not `|| _collect_rc=$?` on the same line, which is easy to misread), then if `_collect_rc -ne 0` and `_parse_collect_records "$_collect_out"` yields no records, set `LOOP_STATUS=panel-failed` and `return 1` before voter dispatch; otherwise continue so stderr-tail + partial KV output still flow through the tee.
- **Reviewer**: dyn-plan-review-collect-or-true-output.txt
- **Concern**: - **correctness** `skills/design/scripts/plan-review-loop.sh:757-764` — Round 1 replaced the original `|| _collect_rc=$?` guard (introduced in `3de7ceaaf`) with `|| true`, so the collector’s exit status is no longer captured on HEAD. That does **not** block `_collect_out` assignment on a non-zero collector exit (bash still fills the command substitution from stdout before evaluating the list’s status), and bash waits for the `2> >(tee …)` process substitution to finish before the assignment completes, so the FD-2 / `plan-review-collector.stderr` tail test can pass. The defect is semantic: without `_collect_rc`, the driver cannot tell a hard collector failure (empty/unparseable stdout) from a partial success, so it keeps going into manifest/slot/voter/tally work and multi-round callers can end in `degraded-empty-collector` instead of an early `panel-failed` round failure. **`|| true` is also redundant for `set -e` abort avoidance here**, because both call sites of `_run_plan_review_round` already run it under `set +e` (`1222-1225`, `1260-1263`). **Suggested fix:** Drop `|| true` and restore explicit status handling—the uncommitted working-tree pattern is the right shape: `set +e` around the collect assignment, `_collect_rc=$?` immediately after (not `|| _collect_rc=$?` on the same line, which is easy to misread), then if `_collect_rc -ne 0` and `_parse_collect_records "$_collect_out"` yields no records, set `LOOP_STATUS=panel-failed` and `return 1` before voter dispatch; otherwise continue so stderr-tail + partial KV output still flow through the tee.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: scripts/ship-pr.sh:152-154
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] run_lint_fix_loop_capture may skip surfacing on empty/malformed LINT_FIX_STATUS with rc=0 Malformed lint-fix stdout could leave tails only on disk Surface when rc!=0 and lint_status is empty or parse fails
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/lint-fix-loop.sh:246-260,418-420
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] _LINT_FIX_STDERR_TAIL_STEM always tracks the last failure; a later Cursor preflight/agent failure without a usable cursor.log.stderr-tail overwrites a prior Codex stem while STDERR_TAIL_PATH still points at cursor.log. Codex fails with rich codex.log.stderr-tail; Cursor preflight fails with empty/minimal tail; callers emit on cursor.log and chat stays silent despite codex.log.stderr-tail on disk. Prefer stem with non-empty .stderr-tail when updating _LINT_FIX_STDERR_TAIL_STEM, or set STDERR_TAIL_PATH to the first non-empty codex/cursor tail at dispatch-failed.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/ship-pr.sh:150-155
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] run_lint_fix_loop_capture omits surfacing when lint-fix exits 0 with empty/missing LINT_FIX_STATUS (plan empty-with-failure). Broken or truncated lint-fix stdout: rc=0, no LINT_FIX_STATUS, stderr-tail on disk; _surface_lint_fix_stderr_tail never runs. Also surface on empty lint_status when a known stderr-tail file exists, or treat empty status as failure.
- **Suggested revision**: Address the concern above.


