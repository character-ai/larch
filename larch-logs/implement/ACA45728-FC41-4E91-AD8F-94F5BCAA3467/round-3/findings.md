### FINDING_1: code-quality: skills/implement/scripts/step2-implement.sh:1064-1080
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] emit_failed_agent_stderr_tail_larch_err is only called from emit_bailed() not from the final manifest status=bailed envelope Agent returns LAUNCHER_EXIT=0 with manifest status bailed after writing stderr; orchestrator gets SIDECAR_LOG KV but no fenced stderr tail in chat Add emit_failed_agent_stderr_tail_larch_err "$TRANSCRIPT_PATH" || true to the bailed) case arm or share a helper with emit_bailed()
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/ship-pr.sh:122-129 and skills/review-and-fix/scripts/review-implement-step5-loop.sh:76-85
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated STDERR_TAIL_PATH / CODER_LOG_FILE stem resolution and emit logic Future parity fixes must be applied in two places and can drift Extract a shared helper in lib-failed-agent-stderr-tail.sh
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/lint-fix-loop.sh:253-301
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Overlapping cursor failure tail-write paths in _run_cursor_record_early_fail and post-agent block Harder to verify no clobber/wrong-source regression on cursor preflight vs agent failure Consolidate into one record-failure helper
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:276
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] step5_surface_lint_stderr_tail called on lint-fix-attempt-cap after applied status Misleading control flow; usually no tail to surface Remove call or guard on non-empty stem variables
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/lint-fix-loop.sh:245-247
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Redundant write_failed_agent_stderr_tail after run-external-agent --stderr-sink Extra disk I/O; possible overwrite if sources differ Skip write when tail file already exists or document intentional redundancy
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/ship-pr.sh:152-154
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] run_lint_fix_loop_capture may skip surfacing on empty/malformed LINT_FIX_STATUS with rc=0 Malformed lint-fix stdout could leave tails only on disk Surface when rc!=0 and lint_status is empty or parse fails
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/ship-pr.sh:2752
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Recovery launcher_stdout files not explicitly deleted Session tmpdir growth over long runs Align with existing IMPLEMENT_TMPDIR cleanup policy or rm after parse
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/lint-fix-loop.sh:246-260,418-420
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] _LINT_FIX_STDERR_TAIL_STEM always tracks the last failure; a later Cursor preflight/agent failure without a usable cursor.log.stderr-tail overwrites a prior Codex stem while STDERR_TAIL_PATH still points at cursor.log. Codex fails with rich codex.log.stderr-tail; Cursor preflight fails with empty/minimal tail; callers emit on cursor.log and chat stays silent despite codex.log.stderr-tail on disk. Prefer stem with non-empty .stderr-tail when updating _LINT_FIX_STDERR_TAIL_STEM, or set STDERR_TAIL_PATH to the first non-empty codex/cursor tail at dispatch-failed.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/ship-pr.sh:150-155
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] run_lint_fix_loop_capture omits surfacing when lint-fix exits 0 with empty/missing LINT_FIX_STATUS (plan empty-with-failure). Broken or truncated lint-fix stdout: rc=0, no LINT_FIX_STATUS, stderr-tail on disk; _surface_lint_fix_stderr_tail never runs. Also surface on empty lint_status when a known stderr-tail file exists, or treat empty status as failure.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:276-277
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] step5_surface_lint_stderr_tail on lint-fix-attempt-cap usually runs after applied status with no stashed stem. Attempt-cap stall: no tail in chat even when earlier attempts failed with tails (stems not retained). Call step5_surface only on failure terminal arms or retain last failure stem across attempts.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-ship-pr.sh:6316-6362
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] #3227 run_lint_fix_loop_capture tests omit LINT_FIX_STATUS=failed even though ship-pr surfaces on failed. A regression in failed-status tail parsing/emission would not fail make test-ship-pr while Step 5 parser tests still pass. Add a failed-status stub with CODER_LOG_FILE and seeded .stderr-tail; assert caller stderr receives the probe.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/implement/scripts/test-cursor-implementer.sh:899-904
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Cursor agent-failure test does not assert redaction/bounds unlike codex harness. Raw secrets in cursor .stderr-tail could ship to chat without CI catching it. Mirror codex redaction/secret assertions on the cursor failure path.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/design/scripts/test-plan-review-loop.sh:2137-2152
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] FD-2 tail test does not assert LOOP_STATUS when collector exits 1 with parseable output. Collector handling could change voting/degraded semantics while the tail marker test still passes. Pin expected LOOP_STATUS (or stable KVs) for write_collect_failing_tail in addition to stderr markers.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/ship-pr.sh:150-155
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan empty-with-failure lint_status guard not implemented in run_lint_fix_loop_capture. rc 0 plus empty LINT_FIX_STATUS would skip caller-scope surfacing despite an on-disk tail. Implement empty-status surfacing or prove lint-fix-loop cannot emit it; add a harness case if realistic.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] risk-integration: scripts/test-ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] #3227 adds many new cases to an already large harness. CI shard runtime or ordering flakes may worsen without functional bugs in the feature. Monitor test-ship-pr duration; split cases if the shard becomes a bottleneck.
- **Suggested revision**: Address the concern above.

### FINDING_16: `51001756e` Apply relevant-checks fixes (Step 5)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `51001756e` Apply relevant-checks fixes (Step 5)
- **Suggested revision**: Address the concern above.

### FINDING_17: `eaab9c8f1` Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `eaab9c8f1` Address code review feedback (round 1)
- **Suggested revision**: Address the concern above.

### FINDING_18: `f3b107fa6` Fix ShellCheck SC1007
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `f3b107fa6` Fix ShellCheck SC1007
- **Suggested revision**: Address the concern above.

### FINDING_19: `475777f42` chore(larch-logs): flush implement run
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `475777f42` chore(larch-logs): flush implement run
- **Suggested revision**: Address the concern above.

### FINDING_20: `3de7ceaaf` Extend stderr-tail surfacing (#3227)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `3de7ceaaf` Extend stderr-tail surfacing (#3227)
- **Suggested revision**: Address the concern above.

### FINDING_21: `2f375cd1e` Fixes #3229: Test cleanup find-failure fail-safe
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `2f375cd1e` Fixes #3229: Test cleanup find-failure fail-safe ---
- **Suggested revision**: Address the concern above.

### FINDING_22: **Producers** call `write_failed_agent_stderr_tail` (redact-tmpdir → redact-secrets, 30-line / 5120-byte cap) on failure-only paths in implement launchers and `lint-fix-loop.sh`, without using `cursor.wrapper.log` as a stderr source.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Producers** call `write_failed_agent_stderr_tail` (redact-tmpdir → redact-secrets, 30-line / 5120-byte cap) on failure-only paths in implement launchers and `lint-fix-loop.sh`, without using `cursor.wrapper.log` as a stderr source.
- **Suggested revision**: Address the concern above.

### FINDING_23: **Consumers** call `emit_failed_agent_stderr_tail_larch_err`, which reads only `${stem}.stderr-tail` (not raw sidecars or wrapper logs), with per-line `sanitize_diagnostic_line`; stems are quoted, not evaluated.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Consumers** call `emit_failed_agent_stderr_tail_larch_err`, which reads only `${stem}.stderr-tail` (not raw sidecars or wrapper logs), with per-line `sanitize_diagnostic_line`; stems are quoted, not evaluated.
- **Suggested revision**: Address the concern above.

### FINDING_24: **Caller-scope surfacing** in `ship-pr.sh` and Step 5 avoids emitting inside FD-2–redirected subshells, matching the documented trust model.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Caller-scope surfacing** in `ship-pr.sh` and Step 5 avoids emitting inside FD-2–redirected subshells, matching the documented trust model.
- **Suggested revision**: Address the concern above.

### FINDING_25: **`run-external-agent.sh` is unchanged**; cursor CI/implement lanes still rely on its producer path where applicable.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`run-external-agent.sh` is unchanged**; cursor CI/implement lanes still rely on its producer path where applicable.
- **Suggested revision**: Address the concern above.

### FINDING_26: **SECURITY.md** documents the expanded lanes and the same partial redaction limits as #3202.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **SECURITY.md** documents the expanded lanes and the same partial redaction limits as #3202. No command injection, path traversal in shell interpolation, hard-coded secrets, or raw-capture `cat` to chat were introduced in the production diff. ---
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/redact-secrets.sh:23-28` — Redaction remains explicitly partial (no opaque bearer tokens, DB strings, PII, etc.). This branch increases how often failure diagnostics reach orchestrator chat; that amplifies the impact of any redaction gap, but does not weaken the redaction pipeline itself. **Suggested fix:** Treat as accepted operational risk per `SECURITY.md`; extend patterns only via deliberate redactor changes, not per-lane emit sites.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/design/scripts/plan-review-loop.sh:757-783` — Collector stderr is still teed live to FD 2/4 before the #3227 `set +e` / parseable-output handling. §3.8 tails go through `render_failed_agent_stderr_tail`; other collector stderr uses `sanitize_diagnostic_line`. This behavior predates #3227; the new harness case only locks it in. **Suggested fix:** None required for #3227 unless you want collector stderr to pass through the full redaction pipe at tee time (separate hardening).
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **architecture** `skills/cleanup/scripts/cleanup.sh:1969-1977` (#3229, same branch) — On nested `find` failure, cleanup skips deletion and retains stale session dirs longer, which can prolong at-rest artifacts under `~/.cache/larch/sessions/`. **Suggested fix:** Out of #3227 scope; already documented as fail-safe retention tradeoff in cleanup harness/docs.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/design/scripts/plan-review-loop.sh:757-765
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Collector subshell uses `|| true`, dropping `_collect_rc` failure handling added in round 1. Collector exits non-zero with empty/unparseable stdout: stderr tail reaches FD 2, but loop continues without `panel-failed` / empty-review guard. Commit staged `set +e` + `_collect_rc` + parseable-output check; remove bare `|| true`.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: scripts/lint-fix-loop.sh:247-292
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] `_LINT_FIX_STDERR_TAIL_STEM` always overwritten by the last external failure. Codex agent fails with rich stderr, then cursor preflight fails: `STDERR_TAIL_PATH` points at cursor and chat shows preflight noise while `codex.log.stderr-tail` is ignored. Prefer first non-empty tail stem, or set stem only when unset / new tail is richer.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: scripts/launch-codex-implement.sh:346, scripts/launch-cursor-implement.sh:314-315
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Auth-retry loops clear sidecar/diag before the final tail write. Multi-attempt auth exhaustion: surfaced tail is only from the last truncated attempt, not the first actionable error. Preserve cumulative stderr across retries or snapshot tail before `: > "$SIDECAR_LOG"`.
- **Suggested revision**: Address the concern above.

### FINDING_33: architecture: scripts/ship-pr.sh:2752-2773
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Recovery waterfall leaves `launcher_stdout` capture files behind. Long recovery runs accumulate orphaned `recovery-*-launcher-*.out` files under `$IMPLEMENT_TMPDIR`. `rm -f` each `launcher_stdout` after parsing, or reuse one temp path per waterfall.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] correctness: scripts/lint-fix-loop.sh:36-39
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] `fail_status` exits do not emit `STDERR_TAIL_PATH`. Agent succeeds then head/forbidden-path validation fails: lint-fix fails without stderr tail in chat. Emit `STDERR_TAIL_PATH` on post-dispatch `fail_status` when a stem tail exists (follow-up).
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: scripts/ship-pr.sh:150-155
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] run_lint_fix_loop_capture omits plan's empty-with-failure surfacing gate Malformed or truncated lint-fix stdout can yield rc=0 and empty LINT_FIX_STATUS while a stderr-tail artifact exists; _surface_lint_fix_stderr_tail is skipped and chat never shows the tail Also surface when lint_status is empty after a failed capture (e.g. rc!=0, non-empty fail_file, or parseable STDERR_TAIL_PATH/CODER_LOG_FILE fallback)
- **Suggested revision**: Address the concern above.

### FINDING_36: **correctness** `skills/design/scripts/plan-review-loop.sh:757-764` — Round 1 replaced the original `|| _collect_rc=$?` guard (introduced in `3de7ceaaf`) with `|| true`, so the collector’s exit status is no longer captured on HEAD. That does **not** block `_collect_out` assignment on a non-zero collector exit (bash still fills the command substitution from stdout before evaluating the list’s status), and bash waits for the `2> >(tee …)` process substitution to finish before the assignment completes, so the FD-2 / `plan-review-collector.stderr` tail test can pass. The defect is semantic: without `_collect_rc`, the driver cannot tell a hard collector failure (empty/unparseable stdout) from a partial success, so it keeps going into manifest/slot/voter/tally work and multi-round callers can end in `degraded-empty-collector` instead of an early `panel-failed` round failure. **`|| true` is also redundant for `set -e` abort avoidance here**, because both call sites of `_run_plan_review_round` already run it under `set +e` (`1222-1225`, `1260-1263`). **Suggested fix:** Drop `|| true` and restore explicit status handling—the uncommitted working-tree pattern is the right shape: `set +e` around the collect assignment, `_collect_rc=$?` immediately after (not `|| _collect_rc=$?` on the same line, which is easy to misread), then if `_collect_rc -ne 0` and `_parse_collect_records "$_collect_out"` yields no records, set `LOOP_STATUS=panel-failed` and `return 1` before voter dispatch; otherwise continue so stderr-tail + partial KV output still flow through the tee.
- **Reviewer**: dyn-plan-review-collect-or-true-output.txt
- **Concern**: - **correctness** `skills/design/scripts/plan-review-loop.sh:757-764` — Round 1 replaced the original `|| _collect_rc=$?` guard (introduced in `3de7ceaaf`) with `|| true`, so the collector’s exit status is no longer captured on HEAD. That does **not** block `_collect_out` assignment on a non-zero collector exit (bash still fills the command substitution from stdout before evaluating the list’s status), and bash waits for the `2> >(tee …)` process substitution to finish before the assignment completes, so the FD-2 / `plan-review-collector.stderr` tail test can pass. The defect is semantic: without `_collect_rc`, the driver cannot tell a hard collector failure (empty/unparseable stdout) from a partial success, so it keeps going into manifest/slot/voter/tally work and multi-round callers can end in `degraded-empty-collector` instead of an early `panel-failed` round failure. **`|| true` is also redundant for `set -e` abort avoidance here**, because both call sites of `_run_plan_review_round` already run it under `set +e` (`1222-1225`, `1260-1263`). **Suggested fix:** Drop `|| true` and restore explicit status handling—the uncommitted working-tree pattern is the right shape: `set +e` around the collect assignment, `_collect_rc=$?` immediately after (not `|| _collect_rc=$?` on the same line, which is easy to misread), then if `_collect_rc -ne 0` and `_parse_collect_records "$_collect_out"` yields no records, set `LOOP_STATUS=panel-failed` and `return 1` before voter dispatch; otherwise continue so stderr-tail + partial KV output still flow through the tee.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] The working tree (not yet on `HEAD`) already implements the `_collect_rc` + parseable-output gate at `766-783`; committing that closes the regression introduced when `eaab9c8f1` swapped `|| _collect_rc=$?` for `|| true`.
- **Reviewer**: dyn-plan-review-collect-or-true-output.txt
- **Concern**: - The working tree (not yet on `HEAD`) already implements the `_collect_rc` + parseable-output gate at `766-783`; committing that closes the regression introduced when `eaab9c8f1` swapped `|| _collect_rc=$?` for `|| true`.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] `skills/design/scripts/test-plan-review-loop.sh:2115-2135` adds a “collector hard fail with empty stdout → panel-failed” case that documents the desired behavior above; it is not present on `HEAD` and would fail against `|| true`-only code until the gate is committed.
- **Reviewer**: dyn-plan-review-collect-or-true-output.txt
- **Concern**: - `skills/design/scripts/test-plan-review-loop.sh:2115-2135` adds a “collector hard fail with empty stdout → panel-failed” case that documents the desired behavior above; it is not present on `HEAD` and would fail against `|| true`-only code until the gate is committed.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] Broader #3227 producer/consumer wiring (`launch-*-implement.sh`, `ship-pr.sh` `_surface_*`, `lint-fix-loop.sh` `STDERR_TAIL_PATH`, `step2-implement.sh` / Step 5 surfacing) matches the plan’s caller-scope emit pattern; no additional correctness defects stood out in those paths for this focus area.
- **Reviewer**: dyn-plan-review-collect-or-true-output.txt
- **Concern**: - Broader #3227 producer/consumer wiring (`launch-*-implement.sh`, `ship-pr.sh` `_surface_*`, `lint-fix-loop.sh` `STDERR_TAIL_PATH`, `step2-implement.sh` / Step 5 surfacing) matches the plan’s caller-scope emit pattern; no additional correctness defects stood out in those paths for this focus area.
- **Suggested revision**: Address the concern above.

