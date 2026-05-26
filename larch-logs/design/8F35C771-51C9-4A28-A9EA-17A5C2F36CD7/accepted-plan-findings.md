### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-foreground-markers.sh:100-623
- **Concern**: Plan adds four new PID-pair lint fixtures but does not update ~22 existing assert_case_clean fences. Scenario: Enabling has_pid_alloc/has_pid_flag in lint-foreground-markers.sh will fail make lint-foreground-markers on the current harness even after skill fences are converted; CI blocks the PR
- **Proposed resolution**: Add LARCH_PAIRED_PID_FILE mktemp/export and --paired-pid-file "$LARCH_PAIRED_PID_FILE" to every passing Family B fixture (cases 1, 4, and all other assert_case_clean blocks), not only the four new negative/positive cases


### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/lint-foreground-markers.sh:345-349
- **Concern**: Planned has_pid_alloc check accepts any export LARCH_PAIRED_PID_FILE line, even when no fresh mktemp allocation exists. Scenario: A copied fence can pass lint while reusing a stale inherited PID-file path across launches, causing clobbered PID files and possible timeout signaling of the wrong run
- **Proposed resolution**: Require an assignment from mktemp under the active session tmpdir in the same fence before export, and add a negative fixture for bare export LARCH_PAIRED_PID_FILE


### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/run-step2-dispatch.sh:86-112
- **Concern**: Child step2-implement overwrites paired PID file. Scenario: Monitor kills implementer child; run-step2-dispatch stays alive without paired teardown
- **Proposed resolution**: Only background root writes PID; unset LARCH_PAIRED_PID_FILE before exec child or skip write in step2-implement when env inherited


### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ci-wait.md:70-79; skills/implement/references/rebase-rebump-subprocedure.md:175-184
- **Concern**: ci-wait migration misses its own edit-in-sync surfaces. Scenario: The plan updates ci-wait.md wording but leaves rebase-rebump prose and related test/docs pinned to synchronous-only, so post-PR guidance conflicts and structural checks can preserve the old contract
- **Proposed resolution**: Update every ci-wait synchronous-only site listed in ci-wait.md, including rebase-rebump-subprocedure and ci-wait exit-trap docs/tests, or explicitly keep ci-wait outside the new paired-PID Family B contract


### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/lib-quiet.sh:185-205; scripts/breadcrumb-monitor.sh:31-51
- **Concern**: Proposed PID writer validates less than the monitor/docs require. Scenario: The helper plan only checks absolute/no-dotdot before writing, while the monitor/docs require session tmpdir scope and symlink rejection; an ambient LARCH_PAIRED_PID_FILE can make scripts write a PID file outside the intended session surface
- **Proposed resolution**: Share or mirror the monitor path validation for LARCH_PAIRED_PID_FILE before writing, including session tmpdir containment, symlink rejection, and regular-file/parent checks, while still failing open for callers


### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:57-73,scripts/ship-pr.sh:2620,skills/implement/scripts/run-step2-dispatch.sh:96-97,scripts/run-step5-review.sh:246-247
- **Concern**: Nested denylisted children would overwrite LARCH_PAIRED_PID_FILE. Scenario: After ci-wait/step2-implement/review-and-fix return, the file holds a dead child PID; monitor timeout then WARN-skips while ship-pr.sh, run-step2-dispatch.sh, or run-step5-review.sh keep running (orphan regression)
- **Proposed resolution**: Call larch_quiet_write_paired_pid_file only on direct background entrypoints (ship-pr, run-step2-dispatch, run-step5-review, collect-agent-results, dispatch-with-waterfall, dispatch-plan-voters); omit ci-wait, step2-implement, review-and-fix; optionally re-write $$ after nested calls return


### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/lib-quiet.sh:185-205; scripts/breadcrumb-monitor.sh:31-53
- **Concern**: The PID-file writer is less strict than the monitor validator. Scenario: Monitor-side validation rejects paths outside session tmpdirs and symlinks, but the new lib-quiet helper is planned to write to any absolute no-dotdot path before the foreground monitor can reject its argv; a malformed or hostile LARCH_PAIRED_PID_FILE could clobber an arbitrary writable file via the predictable tmp path and mv
- **Proposed resolution**: Make larch_quiet_write_paired_pid_file enforce the same session-tmpdir, symlink, regular-file, and parent-directory constraints before writing; use mktemp in the target directory instead of a predictable .tmp.$$ name; warn and return 0 on invalid paths so callers do not abort under set -e


### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/lint-foreground-markers.sh:345-349
- **Concern**: The proposed allocation check can pass on a bare export without allocation. Scenario: The plan says has_pid_alloc should match either LARCH_PAIRED_PID_FILE=.*mktemp or export LARCH_PAIRED_PID_FILE, so a fence that only exports an unset or inherited variable can satisfy CI while still lacking a per-launch pid-file allocation
- **Proposed resolution**: Require an actual assignment from mktemp before the anchor, plus export, or require a single export assignment such as export LARCH_PAIRED_PID_FILE="$(mktemp ...)" under the session breadcrumbs directory; add a negative fixture with only export LARCH_PAIRED_PID_FILE to lock this down


### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.md:5-9
- **Concern**: Plan says reconcile synchronous-only wording with Family B monitor pairing, but authoritative docs require blocking foreground ci-wait (no run_in_background). Scenario: Implementer replaces synchronous contract with background+monitor guidance; violates #842 / test-implement-structure assertion 17; reintroduces leaked-poll risk
- **Proposed resolution**: Keep ci-wait.md synchronous-only; only add optional note that LARCH_PAIRED_PID_FILE write in ci-wait.sh is a no-op unless a future caller backgrounds with a monitor; do not require monitor fences for ci-wait


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/lib-quiet.sh:185-205
- **Concern**: The proposed larch_quiet_write_paired_pid_file validates only absolute/no-.. and writes through a predictable ${LARCH_PAIRED_PID_FILE}.tmp.$$ path. Scenario: An inherited or malicious LARCH_PAIRED_PID_FILE can make a Family B script clobber an arbitrary user-writable absolute path before breadcrumb-monitor.sh gets a chance to reject the monitor argv
- **Proposed resolution**: Make the writer enforce the same session-tmpdir/symlink/regular-file constraints as breadcrumb-monitor.sh, factor a shared validator if needed, and publish via mktemp in the validated parent directory plus mv -f rather than a predictable tmp name


### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:136-149
- **Concern**: Plan omits SECURITY.md update for new timeout process signaling behavior. Scenario: AGENTS.md requires SECURITY.md updates when security-relevant behavior changes; this PR adds monitor-driven SIGTERM/SIGKILL based on a session pid file and documents PID-reuse risk only in breadcrumb-monitor.md
- **Proposed resolution**: Add SECURITY.md coverage near breadcrumb/runtime trust model for paired-pid files, same-UID trust assumptions, path containment, PID reuse, and signal scope


### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/lib-quiet.sh:185-205
- **Concern**: Writer-side pid-file validation is weaker than the documented monitor invariant. Scenario: The plan documents paired-pid paths as absolute, no .., no symlinks, and under session tmpdir, but the proposed lib-quiet helper only checks absolute/no .. before writing; a direct script invocation with LARCH_PAIRED_PID_FILE set could write/rename outside the session surface
- **Proposed resolution**: Add the same session-tmpdir and symlink/path-scope validation used by breadcrumb-monitor, or a shared validation helper, and add lib-quiet tests for outside-tmpdir and symlink rejection


### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2620; skills/implement/scripts/run-step2-dispatch.sh:96-112; scripts/run-step5-review.sh:186-187; scripts/dispatch-plan-voters.sh:138
- **Concern**: The plan is silent on nested Family B scripts overwriting the paired pid file. Scenario: Several planned writers invoke other planned writers synchronously, so the child can overwrite the top-level background script PID; on monitor timeout the helper may signal the nested child while the paired background wrapper survives or handles the child failure and continues
- **Proposed resolution**: Define ownership semantics explicitly, such as first-writer-wins, top-level-only export, or process-group signaling, and add a regression test with a nested Family B stub proving the paired launch is not orphaned


### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:66; skills/implement/references/rebase-rebump-subprocedure.md:184
- **Concern**: Plan updates fences but leaves conflicting normative Family B and ci-wait prose. Scenario: NEVER #16 still instructs exporting five env vars and invoking breadcrumb-monitor without --paired-pid-file; rebase-rebump still says ci-wait.sh must be synchronous even though the plan moves ci-wait into the Family B pairing contract
- **Proposed resolution**: Revise the load-bearing prose in the same PR to mention LARCH_PAIRED_PID_FILE and --paired-pid-file, and reconcile or explicitly carve out ci-wait in rebase-rebump docs


### FINDING_24:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:163-168
- **Concern**: Signal helper plan does not require kill failures to be guarded under set -e. Scenario: If the PID exits between pid-file read and kill -TERM or before kill -KILL, an unguarded kill can make breadcrumb-monitor exit with the kill status instead of the required timeout exit 4
- **Proposed resolution**: Specify kill -TERM, kill -KILL, and kill -0 race handling with guarded commands that warn/return 0 so the timeout path always reaches exit 4


### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-signal-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:88-89
- **Concern**: Proposed KILL-escalation test uses `trap '' TERM; sleep 1860 &` in the test harness parent. Scenario: Bash traps are not inherited by background children; `sleep` still exits on SIGTERM, so the test passes when TERM alone kills the child and never exercises the 5× `kill -0` loop or SIGKILL
- **Proposed resolution**: Launch a TERM-ignoring child in the test body, e.g. `bash -c 'trap "" TERM; while sleep 1; do :; done' &`, write its PID to the paired file, then assert the process is gone only after ~5s (or use `kill -0` polling in the test)


### FINDING_26:
- **Reviewer(s)**: Codex-dyn-signal-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:152-167
- **Concern**: Proposed 32-byte PID read cannot reliably reject all multi-line PID files. Scenario: Reading only the first 32 bytes lets a malformed file with a valid digit prefix and additional newline/content after byte 32 pass validation; ambiguous whitespace stripping could also turn internal newlines into accepted digits if implemented too broadly
- **Proposed resolution**: Read a bounded 33 bytes, reject length greater than 32, strip only one optional final newline, reject any remaining CR/LF or non-ASCII byte under LC_ALL=C, and add explicit empty non-ASCII and multi-line PID tests


### FINDING_27:
- **Reviewer(s)**: Codex-dyn-signal-lifecycle
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/lib-quiet.sh:185-205
- **Concern**: Planned writer says mktemp plus mv but specifies deterministic .tmp.$$ redirection. Scenario: A predictable temp path can be precreated or symlinked before the helper writes, and it does not satisfy the plan's own atomic mktemp+mv invariant
- **Proposed resolution**: Use tmp=$(mktemp "${LARCH_PAIRED_PID_FILE}.tmp.XXXXXX") in the destination directory, write to "$tmp", then mv -f "$tmp" "$LARCH_PAIRED_PID_FILE"; clean up "$tmp" on failure


### FINDING_29:
- **Reviewer(s)**: Codex-dyn-signal-lifecycle
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:66
- **Concern**: Normative Family B invariant still describes only five breadcrumb paths. Scenario: The plan updates fences but does not call out the existing NEVER #16 prose that tells orchestrators to export only the five current LARCH paths, which will conflict with the new PID-file linter contract
- **Proposed resolution**: Update the invariant text to include LARCH_PAIRED_PID_FILE allocation/export and the paired --paired-pid-file monitor argument alongside the existing five paths


### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:5,163-168
- **Concern**: The timeout signaling helper is specified as plain kill -TERM / kill -KILL under set -e without requiring kill failures to be swallowed. Scenario: A stale PID, race between reading the PID file and signaling, or EPERM causes the monitor to exit from kill with status 1 instead of preserving the documented timeout exit 4 path
- **Proposed resolution**: Specify and test that every kill and kill -0 is guarded in conditionals, logs best-effort warnings, and that larch_bm_signal_paired_pid always returns 0 so the timeout branch always reaches exit 4


### FINDING_30:
- **Reviewer(s)**: Cursor-dyn-callsite-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt (UPDATED scripts/ci-wait.sh; skills/implement/scripts/step2-implement.sh; skills/review-and-fix/scripts/review-and-fix.sh; scripts/dispatch-with-waterfall.sh)
- **Concern**: Plan adds larch_quiet_write_paired_pid_file to all nine Family B scripts, but four are only invoked synchronously inside another backgrounded denylist parent (ci-wait inside ship-pr.sh; step2-implement inside run-step2-dispatch.sh; review-and-fix inside run-step5-review.sh; dispatch-with-waterfall inside dispatch-plan-voters.sh). Each child would overwrite LARCH_PAIRED_PID_FILE with its own $$ while the Bash background job PID is the parent.. Scenario: Monitor timeout SIGTERM targets the wrong process (e.g. ci-wait while ship-pr keeps running), leaving orphaned long runners and defeating issue #2848 pairing.
- **Proposed resolution**: Restrict the helper to orchestrator-background entrypoints only (ship-pr, run-step5-review, run-step2-dispatch, collect-agent-results, dispatch-plan-voters), or unset LARCH_PAIRED_PID_FILE before spawning nested denylist children; document the rule in scripts/lib-quiet.md.


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/run-step5-review.sh:246-247
- **Concern**: The plan writes only the top-level script PID even though several Family B entrypoints synchronously wait on child scripts or launch nested workers. Scenario: On timeout, breadcrumb-monitor.sh can terminate run-step5-review.sh while review-and-fix.sh or its launched reviewers continue running, so the actual long-running work remains orphaned despite the new PID-file contract
- **Proposed resolution**: Define the pairing contract as process-tree aware: either launch Family B scripts in their own process group and signal that group, or have larch_quiet_write_paired_pid_file install a TERM trap/child-forwarding helper used by wrappers that synchronously invoke long-running children


### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/run-step2-dispatch.sh:80-86
- **Concern**: The plan says to add the PID write after larch_quiet_init plus larch_quiet_append_done_trap, but this wrapper explicitly must not call larch_quiet_init. Scenario: Following the plan literally redirects the wrapper's stdout/stderr contract and can hide the step2-implement.sh KV output that the orchestrator expects
- **Proposed resolution**: Revise the plan for run-step2-dispatch.sh to preserve the no-init contract and call larch_quiet_write_paired_pid_file immediately after the existing larch_quiet_append_done_trap line only; add a harness assertion that Step 2 KVs still surface normally


### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:5-10
- **Concern**: Signal helper under set -euo pipefail lacks kill failure guards. Scenario: kill -TERM/-KILL or kill -0 on a stale/dead PID returns non-zero and aborts the monitor before exit 4 leaving the background Family B process orphaned and the orchestrator without the intended timeout contract
- **Proposed resolution**: Wrap larch_bm_signal_paired_pid kill/poll calls with || true (or local set +e) and always fall through to exit 4; add harness case for ESRCH/stale PID


### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:67-71
- **Concern**: Proposed PID-file write leaves ci-wait without the breadcrumb done-trap because the later custom EXIT trap overwrites larch_quiet_append_done_trap. Scenario: Any future paired background ci-wait launch writes its PID but never writes LARCH_DONE_SENTINEL; breadcrumb-monitor waits until timeout, then kills a process that may already have completed
- **Proposed resolution**: Move larch_quiet_append_done_trap after the custom trap at line 171 or rewrite the custom trap to call larch_quiet__exit_combo so both ci-wait output publishing and breadcrumb sentinel publishing run


### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/lib-quiet.sh:204-207
- **Concern**: Proposed larch_quiet_write_paired_pid_file validation only checks absolute path and no .., unlike the monitor/doc contract requiring session tmpdir scope and symlink rejection. Scenario: A caller or inherited environment can make any Family B script overwrite an arbitrary absolute path with $$ before the monitor ever validates --paired-pid-file
- **Proposed resolution**: Reuse larch_log_breadcrumbs_under_session_tmp plus symlink and regular-file checks in the helper, or centralize the same path validator used by breadcrumb-monitor.sh


