### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-cursor-implement.sh:291-326
- **Concern**: Plan background and launch-cursor-implement step treat cursor-implement as capture-stdout with run-external-agent producing a good ${TRANSCRIPT_PATH}.stderr-tail; code uses --capture-stdout-only with run-external-agent backgrounded and agent I/O merged to SIDECAR_LOG (2>&1), so select_failed_agent_stderr_source never reads SIDECAR_LOG and may tail .diag or an empty/partial transcript instead of agent stderr.. Scenario: Failed cursor implement runs surface transcript or generic diag in chat while real stderr stays in SIDECAR_LOG only; consumer-only step2 emit_bailed change is insufficient.
- **Proposed resolution**: In launch-cursor-implement.sh failure block (mirror codex-implement), add write_failed_agent_stderr_tail from SIDECAR_LOG or _FAILURE_OUTPUT onto TRANSCRIPT_PATH; tighten plan Background and ### UPDATED: launch-cursor-implement.sh to require this producer unless a harness proves SIDECAR-sourced bytes in the tail file.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2049-2075
- **Concern**: ship-pr.sh fix-loop passes --output "$tier_out" but the plan only names $output for _surface_ci_stderr_tail at the primary CI-launcher site.. Scenario: Implementer passes recovery-waterfall $output at the fix-loop choke point; emit_failed_agent_stderr_tail_larch_err looks for the wrong stem and chat stays silent despite ${tier_out}.stderr-tail on disk.
- **Proposed resolution**: Spell the fix-loop stem explicitly ($tier_out) in ### UPDATED: scripts/ship-pr.sh and call _surface_ci_stderr_tail "$tier_out" on the failure branch before _ci_fix_rollback/continue (including first-fixer-non-health return at ~2081 if that path skips the generic failure block).

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:252-258
- **Concern**: Planned `run_cursor` producer uses `cursor.wrapper.log` but `--capture-stdout` already tails `cursor.log`. Scenario: `run-external-agent.sh` writes `${run_dir}/cursor.log.stderr-tail` from merged agent output; `write_failed_agent_stderr_tail` on `cursor.wrapper.log` can overwrite it with wrapper chatter only
- **Proposed resolution**: After verifying non-zero exit, consumer-only `emit_failed_agent_stderr_tail_larch_err "$run_dir/cursor.log" || true`; add `write_failed_agent_stderr_tail` only if that tail file is missing, sourcing `cursor.log` not `cursor.wrapper.log`

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/launch-cursor-implement.sh:291-303
- **Concern**: Plan checks `--capture-stdout`; launcher uses `--capture-stdout-only` plus outer `>SIDECAR_LOG 2>&1`. Scenario: Mis-verification may add `write_failed_agent_stderr_tail "$SIDECAR_LOG" …` and clobber a good `${TRANSCRIPT_PATH}.stderr-tail` from `.diag`/transcript with wrapper noise
- **Proposed resolution**: Verify `${TRANSCRIPT_PATH}.stderr-tail` after failure; if present, consumer-only via `step2-implement.sh`; if absent, write from `${TRANSCRIPT_PATH}.diag` or `$SIDECAR_LOG`, not assume `--capture-stdout`

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:123-127
- **Concern**: `lint-fix-loop.sh` stderr is redirected to `fail_file`. Scenario: `emit_failed_agent_stderr_tail_larch_err` inside `run_codex`/`run_cursor` lands in `fail_file`, not chat, for ship-pr CI/checks paths; isolated `test-lint-fix-loop.sh` can still pass
- **Proposed resolution**: After the `lint-fix-loop.sh` call (or in `_rcc_handle_fix_status`), surface `${run_dir}/codex.log.stderr-tail` or `${run_dir}/cursor.log.stderr-tail` via `_surface_ci_stderr_tail` / `emit_failed_agent_stderr_tail_larch_err` using `LINT_FIX_RUN_DIR`/`CODER_LOG_FILE` from stdout when present; keep in-loop emit only for orchestrator-direct invocations

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:252-258
- **Concern**: `run_cursor` uses `--capture-stdout`. Scenario: `run-external-agent.sh` already writes `${run_dir}/cursor.log.stderr-tail` on failure; an unconditional `write_failed_agent_stderr_tail` from `cursor.wrapper.log` can clobber with wrapper/progress noise
- **Proposed resolution**: Match codex-ci/cursor-implement: verify mode first; on failure emit only if `${run_dir}/cursor.log.stderr-tail` is missing, then producer-write from the real capture path

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:11-12
- **Concern**: Background mislabels cursor lanes as `--capture-stdout`. Scenario: `launch-cursor-implement.sh` and `launch-cursor-ci.sh` use `--capture-stdout-only`; implementer may add redundant/wrong producer writes
- **Proposed resolution**: Fix the background bullet; in `launch-cursor-implement.sh` verification, require `--capture-stdout-only` and treat existing `${TRANSCRIPT_PATH}.stderr-tail` as sufficient before any producer edit

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:242-259
- **Concern**: Plan adds on-failure tail write/emit inside run_cursor but the function never propagates run-external-agent exit status. Scenario: Cursor agent failures still make run_cursor succeed; the proposed write/emit branch never runs and lint-fix cursor failures stay silent
- **Proposed resolution**: Add cursor_rc capture and return (mirror run_codex: `|| cursor_rc=$?` then `return "$cursor_rc"`) before relying on in-function failure hooks

### FINDING_9:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:242-258 (run_cursor)
- **Concern**: Plan prescribes adding `write_failed_agent_stderr_tail "$run_dir/cursor.wrapper.log" "$run_dir/cursor.log"` in run_cursor on failure — but run_cursor uses `--capture-stdout`, so `run-external-agent.sh` already calls `write_failed_agent_stderr_tail "$run_dir/cursor.log" "$run_dir/cursor.log"` internally, writing `cursor.log.stderr-tail` from cursor's actual captured output. Scenario: Following the plan's producer-write instruction clobbers the good tail (cursor's real stdout/stderr) with cursor.wrapper.log (run-external-agent.sh's progress messages) — exactly the "Failure mode #1" the plan itself warns against; the resulting tail would contain wrapper chatter, not cursor's error output
- **Proposed resolution**: Drop the producer write for `run_cursor`; only add the consumer: `emit_failed_agent_stderr_tail_larch_err "$run_dir/cursor.log" \|\| true`. The plan's own "Approach" already states: "Where run-external-agent.sh already writes it (cursor capture-stdout lanes), add nothing."

### FINDING_10:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt (Background + UPDATED: launch-cursor-implement.sh)
- **Concern**: Background section states cursor-ci and cursor-implement "route through `run-external-agent --capture-stdout`"; both launchers actually use `--capture-stdout-only` (launch-cursor-ci.sh:201, launch-cursor-implement.sh:295). Scenario: The plan's binary decision tree ("default vs --capture-stdout") has no branch for `--capture-stdout-only`; an implementer who takes the background at face value, finds `--capture-stdout-only`, concludes it is "not --capture-stdout", and follows the codex-implement producer-write template for cursor-implement would add an unnecessary write from the wrong source file
- **Proposed resolution**: Correct the Background to note that both cursor-ci and cursor-implement use `--capture-stdout-only`; extend the verification instruction to note that `--capture-stdout-only` also produces `${OUTPUT}.stderr-tail` (via `${OUTPUT}.diag` as the source), so no producer edit is needed for either cursor lane

### FINDING_11:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-cursor-implement.sh:290-326
- **Concern**: Plan background treats cursor-implement as producer-complete via run-external-agent capture-stdout; launcher uses --capture-stdout-only, backgrounds run-external-agent, and redirects the wrapper to SIDECAR_LOG while agent output is split across TRANSCRIPT/.diag. Scenario: Only step2 consumer emit may surface run-external-agent .diag/progress in chat, not actionable agent stderr already routed to SIDECAR_LOG (append_launch_failure already prefers SIDECAR)
- **Proposed resolution**: Add explicit on-failure write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" in launch-cursor-implement (mirror codex-implement); do not rely on consumer-only unless verification shows SIDECAR marker bytes in ${TRANSCRIPT}.stderr-tail

### FINDING_12:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:242-259
- **Concern**: Plan proposes `write_failed_agent_stderr_tail "$run_dir/cursor.wrapper.log" "$run_dir/cursor.log"` as the producer step for `run_cursor` on failure, but `cursor.wrapper.log` contains only `run-external-agent.sh`'s own progress messages (❌/⏳). With `--capture-stdout`, `run-external-agent.sh` internally redirects cursor's stdout+stderr to `cursor.log` before backgrounding the process; the outer `> cursor.wrapper.log 2>&1` never receives cursor's output. `run-external-agent.sh` already calls `write_failed_agent_stderr_tail cursor.log cursor.log` on non-zero exit (capture_stdout path in `select_failed_agent_stderr_source`), so `cursor.log.stderr-tail` is produced correctly before `run_cursor` returns.. Scenario: Implementing the plan as written would overwrite the existing correct `cursor.log.stderr-tail` (sourced from cursor's actual output) with a tail of wrapper progress lines; the tail surfaced to chat becomes "❌ cursor agent: FAILED (exit code 1, Xs elapsed...)" instead of cursor's diagnostic output — defeating the feature for this lane.
- **Proposed resolution**: Drop the producer write for `run_cursor`; it is already a no-op lane. Only add the consumer emit after a non-zero return: `emit_failed_agent_stderr_tail_larch_err "$run_dir/cursor.log" \|\| true`. The plan's analogy to `run_codex` does not hold because `run_codex` uses default (no-capture) mode so codex's stderr reaches `codex_wrapper_log` through inherited fd2, while `run_cursor` uses `--capture-stdout` which intercepts cursor's fd1+fd2 into `cursor.log` inside `run-external-agent.sh` before the outer redirect applies.

### FINDING_13:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:252-258
- **Concern**: Plan claims run_cursor produces no tail, but --capture-stdout mode already makes run-external-agent.sh write cursor.log.stderr-tail from cursor.log. Scenario: Plan proposes write_failed_agent_stderr_tail "$run_dir/cursor.wrapper.log" "$run_dir/cursor.log" which overwrites the already-correct tail (sourced from cursor's actual output in cursor.log) with run-external-agent.sh wrapper progress messages from cursor.wrapper.log — exact Failure Mode #1 from the plan's own edge-case section
- **Proposed resolution**: For run_cursor in lint-fix-loop, omit the producer write (run-external-agent.sh already handles it via --capture-stdout); add only the consumer emit: emit_failed_agent_stderr_tail_larch_err "$run_dir/cursor.log" || true on non-zero rc, mirroring the codex-ci pattern

### FINDING_14:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/launch-cursor-implement.sh:291-295
- **Concern**: Plan's "verify first" hedge names the wrong flag: it says verify launcher uses run-external-agent --capture-stdout, but actual flag is --capture-stdout-only (mutually exclusive per run-external-agent.sh:94-96). Scenario: An implementer who reads --capture-stdout-only ≠ --capture-stdout may follow the "If it does NOT capture-stdout, mirror codex-implement producer write" branch, calling write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" which would overwrite the already-correct ${TRANSCRIPT_PATH}.stderr-tail (sourced from ${TRANSCRIPT_PATH}.diag = cursor's actual stderr) with $SIDECAR_LOG content (run-external-agent.sh wrapper messages)
- **Proposed resolution**: Update the plan to name the actual flag --capture-stdout-only and clarify that both --capture-stdout and --capture-stdout-only modes satisfy the "tail already produced" criterion; confirm that select_failed_agent_stderr_source with capture_stdout_only=true finds ${TRANSCRIPT_PATH}.diag, so no producer write is needed

### FINDING_15:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh (proposed run_codex/run_cursor consumer emit) + scripts/ship-pr.sh:115-131 + skills/review-and-fix/scripts/review-implement-step5-loop.sh:241
- **Concern**: emit_failed_agent_stderr_tail_larch_err inside lint-fix-loop.sh is swallowed at both production call sites. Scenario: larch_quiet_init (lib-quiet.sh:73-78) snapshots FD 2 into FD 4 at process start. ship-pr.sh:127 launches lint-fix-loop.sh with 2>"$fail_file"; review-implement-step5-loop.sh:241 launches it with >"$lint_out" 2>&1. Both redirect FD 2 before larch_quiet_init runs, so FD 4 = captured-to-file descriptor, not chat. Any emit_failed_agent_stderr_tail_larch_err call inside run_codex/run_cursor writes to that file, not to the orchestrator. The plan's own FD-2 mitigation says "emit from the consumer scope whose stderr reaches the orchestrator," but the proposed lint-fix-loop.sh changes violate this for both production callers. The test (test-lint-fix-loop.sh) calls lint-fix-loop.sh without the production 2> redirect so it would pass while production is silently broken.
- **Proposed resolution**: Keep the producer writes (write_failed_agent_stderr_tail) in run_codex/run_cursor — they write the tail file to disk regardless of FD-2 redirect. Remove the consumer emit_failed_agent_stderr_tail_larch_err from run_codex/run_cursor. Add a consumer in ship-pr.sh's run_lint_fix_loop_capture (lines 115-131) after the subprocess exits: have lint-fix-loop.sh emit LINT_FIX_STDERR_TAIL_PATH=<path> via emit_kv (FD 3) on failure, then parse that path from $output and call _surface_ci_stderr_tail from the caller scope whose FD 4 reaches chat. Apply the same pattern to review-implement-step5-loop.sh:241's post-exit handling.

### FINDING_16:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh (proposed run_codex/run_cursor emit) + scripts/ship-pr.sh:123-127 + skills/review-and-fix/scripts/review-implement-step5-loop.sh:241
- **Concern**: emit_failed_agent_stderr_tail_larch_err inside run_codex/run_cursor is inside a FD-2 capturing scope; larch_err routes to caller's capture file, not chat. Scenario: run_lint_fix_loop_capture calls lint-fix-loop.sh with output=$(... 2>"$fail_file"); review-implement-step5-loop.sh calls it with >"$lint_out" 2>&1. larch_quiet_init in lint-fix-loop.sh then does exec 4>&2, capturing the redirected FD2 (a file) as FD4. larch_err->>&4->file, never chat. The LARCH_QUIET_DISABLE=1 test bypasses quiet-init so FD2 goes to terminal and the test passes — a false assurance
- **Proposed resolution**: Move the emit to the calling scope where FD4->chat: in run_lint_fix_loop_capture (ship-pr.sh:114-132) add a _surface_ci_stderr_tail-style call after the $(...) returns non-zero; similarly at review-implement-step5-loop.sh:241-244. Alternatively emit the tail path as a stdout KV (e.g. STDERR_TAIL_PATH=...) from lint-fix-loop.sh so callers in FD4->chat context can re-emit it.

### OOS_1:
- **Description**: Resolve-conflict CI launches omitted from `_surface_ci_stderr_tail`. Scenario: Failed `launch-*-ci.sh resolve-conflict` runs capture launcher output to `fail_file` with the same swallow pattern as the fix loop
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:3278-3290
- **Phase**: design
