Reviewing the cited scripts to confirm how findings overlap before merging.
Structured aggregator output (plain text for `aggregator-output.txt`):

### FINDING_1: cursor-implement stderr may not reach chat (wrong/missing tail source)
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, unknown-slot
- **Severity**: important
- **Concern**: The plan treats cursor-implement as a `--capture-stdout` lane where `run-external-agent.sh` reliably produces `${TRANSCRIPT_PATH}.stderr-tail`, but `launch-cursor-implement.sh` uses `--capture-stdout-only`, backgrounds the wrapper, and redirects wrapper I/O to `SIDECAR_LOG` (`>SIDECAR_LOG 2>&1`). Agent output is split across `TRANSCRIPT_PATH` / `.diag` while actionable stderr may sit only in `SIDECAR_LOG`. `select_failed_agent_stderr_source` may therefore tail `.diag` or a partial transcript instead of agent stderr; a consumer-only `step2` emit is insufficient if the tail file never gets SIDECAR-sourced bytes. Reviewers disagree whether the fix is an explicit producer write from `SIDECAR_LOG` (mirror codex-implement) versus verify-first / consumer-only to avoid clobbering an already-good `${TRANSCRIPT_PATH}.stderr-tail` from `.diag`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In launch-cursor-implement.sh failure block (mirror codex-implement), add write_failed_agent_stderr_tail from SIDECAR_LOG or _FAILURE_OUTPUT onto TRANSCRIPT_PATH; tighten plan Background and ### UPDATED: launch-cursor-implement.sh to require this producer unless a harness proves SIDECAR-sourced bytes in the tail file.
  - From Cursor-Edge: Verify `${TRANSCRIPT_PATH}.stderr-tail` after failure; if present, consumer-only via `step2-implement.sh`; if absent, write from `${TRANSCRIPT_PATH}.diag` or `$SIDECAR_LOG`, not assume `--capture-stdout`
  - From unknown-slot: Add explicit on-failure write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" in launch-cursor-implement (mirror codex-implement); do not rely on consumer-only unless verification shows SIDECAR marker bytes in ${TRANSCRIPT}.stderr-tail
  - From unknown-slot: Update the plan to name the actual flag --capture-stdout-only and clarify that both --capture-stdout and --capture-stdout-only modes satisfy the "tail already produced" criterion; confirm that select_failed_agent_stderr_source with capture_stdout_only=true finds ${TRANSCRIPT_PATH}.diag, so no producer write is needed

### FINDING_2: ship-pr CI fix-loop surfaces stderr from wrong output stem
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The fix-loop passes `--output "$tier_out"` to CI launchers, but the plan only names `$output` for `_surface_ci_stderr_tail` at the primary CI-launcher site. If recovery uses `$output` at the fix-loop choke point, `emit_failed_agent_stderr_tail_larch_err` may look for the wrong stem while `${tier_out}.stderr-tail` already exists on disk, so chat stays silent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell the fix-loop stem explicitly ($tier_out) in ### UPDATED: scripts/ship-pr.sh and call _surface_ci_stderr_tail "$tier_out" on the failure branch before _ci_fix_rollback/continue (including first-fixer-non-health return at ~2081 if that path skips the generic failure block).

### FINDING_3: lint-fix `run_cursor` producer from `cursor.wrapper.log` can clobber good tail
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation, unknown-slot
- **Severity**: important
- **Concern**: The plan adds `write_failed_agent_stderr_tail` from `cursor.wrapper.log` on failure, but `run_cursor` uses `--capture-stdout`, so `run-external-agent.sh` already writes `${run_dir}/cursor.log.stderr-tail` from merged agent output in `cursor.log`. `cursor.wrapper.log` only holds wrapper/progress lines; an unconditional producer write can overwrite the correct tail with wrapper chatter (the plan’s own Failure mode #1).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: After verifying non-zero exit, consumer-only `emit_failed_agent_stderr_tail_larch_err "$run_dir/cursor.log" || true`; add `write_failed_agent_stderr_tail` only if that tail file is missing, sourcing `cursor.log` not `cursor.wrapper.log`
  - From Cursor-Innovation: Match codex-ci/cursor-implement: verify mode first; on failure emit only if `${run_dir}/cursor.log.stderr-tail` is missing, then producer-write from the real capture path
  - From unknown-slot: Drop the producer write for `run_cursor`; only add the consumer: `emit_failed_agent_stderr_tail_larch_err "$run_dir/cursor.log" \|\| true`. The plan's own "Approach" already states: "Where run-external-agent.sh already writes it (cursor capture-stdout lanes), add nothing."
  - From unknown-slot: Drop the producer write for `run_cursor`; it is already a no-op lane. Only add the consumer emit after a non-zero return: `emit_failed_agent_stderr_tail_larch_err "$run_dir/cursor.log" \|\| true`. The plan's analogy to `run_codex` does not hold because `run_codex` uses default (no-capture) mode so codex's stderr reaches `codex_wrapper_log` through inherited fd2, while `run_cursor` uses `--capture-stdout` which intercepts cursor's fd1+fd2 into `cursor.log` inside `run-external-agent.sh` before the outer redirect applies.
  - From unknown-slot: For run_cursor in lint-fix-loop, omit the producer write (run-external-agent.sh already handles it via --capture-stdout); add only the consumer emit: emit_failed_agent_stderr_tail_larch_err "$run_dir/cursor.log" || true on non-zero rc, mirroring the codex-ci pattern

### FINDING_4: `run_cursor` does not propagate `run-external-agent` exit status
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds on-failure tail write/emit inside `run_cursor`, but the function never propagates `run-external-agent` exit status (unlike `run_codex` with `|| codex_rc=$?` and `return "$codex_rc"`). Cursor agent failures can leave `run_cursor` succeeding, so failure hooks never run and lint-fix cursor failures stay silent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add cursor_rc capture and return (mirror run_codex: `|| cursor_rc=$?` then `return "$cursor_rc"`) before relying on in-function failure hooks

### FINDING_5: in-loop `emit_failed_agent_stderr_tail_larch_err` is swallowed by caller FD 2 redirects
- **Reviewer(s)**: Cursor-Innovation, unknown-slot
- **Severity**: important
- **Concern**: `emit_failed_agent_stderr_tail_larch_err` inside `lint-fix-loop.sh` `run_codex`/`run_cursor` runs after `larch_quiet_init` snapshots FD 2 into FD 4. Production callers redirect FD 2 before subprocess start (`ship-pr.sh` `run_lint_fix_loop_capture` uses `2>"$fail_file"`; `review-implement-step5-loop.sh` uses `2>&1` into a capture file), so `larch_err` goes to the capture file, not chat. Isolated `test-lint-fix-loop.sh` without those redirects can pass while production stays silent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After the `lint-fix-loop.sh` call (or in `_rcc_handle_fix_status`), surface `${run_dir}/codex.log.stderr-tail` or `${run_dir}/cursor.log.stderr-tail` via `_surface_ci_stderr_tail` / `emit_failed_agent_stderr_tail_larch_err` using `LINT_FIX_RUN_DIR`/`CODER_LOG_FILE` from stdout when present; keep in-loop emit only for orchestrator-direct invocations
  - From unknown-slot: Keep the producer writes (write_failed_agent_stderr_tail) in run_codex/run_cursor — they write the tail file to disk regardless of FD-2 redirect. Remove the consumer emit_failed_agent_stderr_tail_larch_err from run_codex/run_cursor. Add a consumer in ship-pr.sh's run_lint_fix_loop_capture (lines 115-131) after the subprocess exits: have lint-fix-loop.sh emit LINT_FIX_STDERR_TAIL_PATH=<path> via emit_kv (FD 3) on failure, then parse that path from $output and call _surface_ci_stderr_tail from the caller scope whose FD 4 reaches chat. Apply the same pattern to review-implement-step5-loop.sh:241's post-exit handling.
  - From unknown-slot: Move the emit to the calling scope where FD4->chat: in run_lint_fix_loop_capture (ship-pr.sh:114-132) add a _surface_ci_stderr_tail-style call after the $(...) returns non-zero; similarly at review-implement-step5-loop.sh:241-244. Alternatively emit the tail path as a stdout KV (e.g. STDERR_TAIL_PATH=...) from lint-fix-loop.sh so callers in FD4->chat context can re-emit it.

### FINDING_6: plan Background mislabels cursor lanes as `--capture-stdout`
- **Reviewer(s)**: Cursor-Innovation, unknown-slot
- **Severity**: important
- **Concern**: Background states cursor-ci and cursor-implement use `run-external-agent --capture-stdout`, but both launchers use `--capture-stdout-only`. The plan’s binary tree has no branch for that flag; implementers may follow the wrong producer template or skip verification that an existing `${OUTPUT}.stderr-tail` is sufficient.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Fix the background bullet; in `launch-cursor-implement.sh` verification, require `--capture-stdout-only` and treat existing `${TRANSCRIPT_PATH}.stderr-tail` as sufficient before any producer edit
  - From unknown-slot: Correct the Background to note that both cursor-ci and cursor-implement use `--capture-stdout-only`; extend the verification instruction to note that `--capture-stdout-only` also produces `${OUTPUT}.stderr-tail` (via `${OUTPUT}.diag` as the source), so no producer edit is needed for either cursor lane
