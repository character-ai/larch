### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:2356-2382
- **Concern**: Vendor-loop exhaustion harness still expects exit 4 stall. Scenario: Plan Decision 3 replaces terminal exit_stall at scripts/ship-pr.sh:2693 with BAIL_REASON=ci-fix-exhausted and exit 3, but Files to modify omits scripts/test-ship-pr.sh. The fix-loop section test vendor_loop_ci_fix_exhausted (make test-ship-pr-fix-loop) still asserts rc 4 and STALL_STEP=10-max-retries
- **Proposed resolution**: Add scripts/test-ship-pr.sh to the plan and update that case to expect exit 3, BAIL_REASON=ci-fix-exhausted, and BAIL_NEEDS_USER_INPUT=false (no STALL_STEP=10-max-retries); list make test-ship-pr-fix-loop alongside the other Bash targets in Testing strategy

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2567-2693; python/ci_monitor.py:1019-1064
- **Concern**: Planned ci-fix-exhausted routing is too broad and can fire after no fixer ran. Scenario: When logs or jobs stay in progress for the outer retry window, the loop defers vendor dispatch on every attempt, then the proposed terminal exit-3 fix-exhausted path would send a pending CI run to the autonomous code fixer
- **Proposed resolution**: Track whether a vendor/per-job fix was actually attempted against ready failure data; only emit ci-fix-exhausted for that case. Preserve the existing stall/wait behavior for still-in-progress or unclassifiable-no-fix attempts.

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2567-2693; python/ci_monitor.py:1021-1064
- **Concern**: ci-fix-exhausted routing can fire when no fix attempt ran. Scenario: If logs or jobs stay in_progress through the 3-attempt backoff, the proposed terminal status can route to autonomous CI fix even though no failure log was ready and no fixer waterfall exhausted.
- **Proposed resolution**: Track whether a ready-log fix attempt actually ran; emit ci-fix-exhausted only for true fixer exhaustion, and keep the existing stall/wait behavior for still-in-progress cases.

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:1169-1175; scripts/ship-pr.sh:2679-2693
- **Concern**: New ci-fix-exhausted token lacks the BAIL_FAILURE_DETAIL_LOG contract. Scenario: The autonomous Step 8 path says to redact and read BAIL_FAILURE_DETAIL_LOG, but the plan only sets BAIL_REASON=ci-fix-exhausted before exit 3.
- **Proposed resolution**: When setting ci-fix-exhausted, also set BAIL_FAILURE_DETAIL_LOG to a tmpdir diagnostic log, or update Step 8 to treat that supplemental log as optional for this token.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:2356-2382
- **Concern**: Plan omits harness updates for vendor outer-loop exhaustion still asserting exit 4 + STALL_STEP=10-max-retries. Scenario: After run_evaluate_failure exits 3 with BAIL_REASON=ci-fix-exhausted, make test-ship-pr-fix-loop (fix-loop section) fails on vendor_loop_ci_fix_exhausted
- **Proposed resolution**: Add scripts/test-ship-pr.sh to Files to modify; change that case to assert rc 3, BAIL_REASON=ci-fix-exhausted, and BAIL_NEEDS_USER_INPUT=false (not STALL_STEP max-retries)

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:3398-3432
- **Concern**: Same gap for ci_fix_exhausted local fix-loop exhaustion (exit 4 stall). Scenario: Second fix-loop regression in the same make target breaks on the same routing change
- **Proposed resolution**: Update that case to exit 3 + ci-fix-exhausted; extend Testing strategy to name scripts/test-ship-pr.sh explicitly (not only the 2632 inc)

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-ship-pr-fix-loop-2632.inc.sh:1-4
- **Concern**: Plan adds #3334 regressions only in the 2632 inc, which is not sourced from test-ship-pr.sh. Scenario: New deterministic-no-rerun / transient-still-reruns cases never run under make test-ship-pr-fix-loop (shard 14)
- **Proposed resolution**: Source the inc from the fix-loop section (restore one source line) or add equivalent cases inline in scripts/test-ship-pr.sh; do not rely on the inc alone

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/ship-pr.sh:2693; python/ci_monitor.py:1057-1064; skills/implement/SKILL.md:1169-1182
- **Concern**: 1. Plan expands the deterministic-rerun fix into a new ci-fix-exhausted autonomous path. Scenario: The minimum fix is to gate the blind rerun so deterministic failures enter the existing fix loop. Adding a new exit-3 bail token, orchestrator trigger, Python status, and Step 8 prose changes broadens behavior after fixes already exhausted and increases loop/triage risk without being required to stop the no-fix rerun churn.
- **Proposed resolution**: Keep this PR to the transient-vs-deterministic rerun gate. Leave max-retries as the existing stall path and defer ci-fix-exhausted autonomous routing to a separate design if still wanted.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2693; python/ci_monitor.py:1057-1064; skills/implement/SKILL.md:1169
- **Concern**: The proposed ci-fix-exhausted exit-3 routing is both extra scope and too broad. Scenario: The shared exhaustion point also covers cases where logs stayed in progress or unreadable and no fixer actually exhausted; the plan would send those to autonomous main-agent CI edits without usable failure evidence
- **Proposed resolution**: Keep the existing stall/waterfall-failed behavior, or gate ci-fix-exhausted on a ready deterministic log plus an actual exhausted fixer dispatch

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:2356-2382
- **Concern**: Plan changes vendor outer exhaustion to exit 3 with `ci-fix-exhausted` but does not list this inline fix-loop case; it still asserts exit 4 and `STALL_STEP=10-max-retries`.. Scenario: `make test-ship-pr-fix-loop` (shard 14) fails after `run_evaluate_failure` stops calling `exit_stall` at `scripts/ship-pr.sh:2693`, or implementers keep exit 4 and miss Decision 3.
- **Proposed resolution**: Update `vendor_loop_ci_fix_exhausted` to expect exit 3, `BAIL_REASON=ci-fix-exhausted`, and autonomous exit-3 state (`BAIL_NEEDS_USER_INPUT=false`, mirroring `scripts/test-ship-pr-fix-loop-2632.inc.sh:63-64`).

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:2356-2382
- **Concern**: The plan changes vendor CI-fix exhaustion from exit 4 stall to exit 3 ci-fix-exhausted, but only names new Bash regressions in scripts/test-ship-pr-fix-loop-2632.inc.sh and does not update this existing harness case that still asserts exit 4 and STALL_STEP=10-max-retries.. Scenario: make test-ship-pr-fix-loop will keep failing after the proposed ship-pr.sh change, or the implementation may preserve the old stall path and miss the new acceptance criterion.
- **Proposed resolution**: Update this existing vendor_loop_ci_fix_exhausted case to expect exit 3, BAIL_REASON=ci-fix-exhausted, and BAIL_NEEDS_USER_INPUT=false/autonomous routing as appropriate.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-bash-python-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2499-2514; scripts/gh-run-logs.sh:50-56; python/ci_monitor.py:496-500,996-1006
- **Concern**: Bash retry gate plan does not require gh-run-logs success before classifying, while Python gates rerun on logs.state == ready. Scenario: If gh-run-logs itself fails with transient text, Bash may rerun but Python treats the log as unreadable and enters the fix loop
- **Proposed resolution**: Require gh_logs_rc == 0 before Bash calls is_transient_net_signature for rerun; any non-zero log fetch goes to the fix loop

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-bash-python-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2127-2128,2140-2172,2679-2693; python/ci_monitor.py:910-963,1051-1064,1183-1192
- **Concern**: Exhaustion mapping can collapse push/launcher-environment failures into ci-fix-exhausted despite the plan saying those stay STALLED. Scenario: Push failed or no launcher tier can route to autonomous main-agent CI fix instead of a stall, and Bash lacks a reason on return 1 to preserve parity
- **Proposed resolution**: Keep non-code-fix failures as immediate STALLED in both paths; only map actual deterministic fixer exhaustion to ci-fix-exhausted

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-exit-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:2356-2382
- **Concern**: Vendor outer-loop exhaustion test still expects exit 4 and STALL_STEP=10-max-retries. Scenario: After run_evaluate_failure switches exhaustion to BAIL_REASON=ci-fix-exhausted and exit 3, make test-ship-pr-fix-loop (and full test-ship-pr) fails on assert_rc 4 / STALL_STEP=10-max-retries even though the plan only adds scripts/test-ship-pr-fix-loop-2632.inc.sh
- **Proposed resolution**: Add an explicit plan step to rewrite this case: assert_rc 3, BAIL_REASON=ci-fix-exhausted, no STALL_STEP=10-max-retries (and keep rebase-storm cases on exit 4 unchanged)

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-exit-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2567-2569,2638-2679,2692-2693
- **Concern**: The shared max-retries tail is not only vendor-fix exhaustion. Scenario: With the proposed ci-fix-exhausted replacement, a run where gh-run-logs stays rc=3 through all attempts could exit 3 and trigger main-agent CI edits even though no fix path ran and CI may still be in flight
- **Proposed resolution**: Track whether a real per-job/vendor fix path ran and exhausted; emit BAIL_REASON=ci-fix-exhausted with BAIL_NEEDS_USER_INPUT=false only for that case, and keep no-log/in-progress exhaustion on the existing stall path

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-exit-contracts
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/ci-decide.md:5-7
- **Concern**: The plan leaves an adjacent contract doc saying vendor-fix exhaustion is exit 4. Scenario: After the change, ci-decide.md would still describe run_evaluate_failure vendor exhaustion as exit_stall with STALL_STEP=10-max-retries, contradicting the new autonomous exit-3 token
- **Proposed resolution**: Update this contract sentence to distinguish fix-attempts-exhausted as user-input exit 3, ci-fix-exhausted as autonomous exit 3, and rebase-count exhaustion as exit 4

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-exit-contracts
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-ship-pr.sh:2356-2382
- **Concern**: The existing vendor exhaustion regression still pins exit 4, but the plan only names the included fix-loop test file. Scenario: make test-ship-pr-fix-loop will fail or keep the old exit-4 contract after run_evaluate_failure changes to ci-fix-exhausted
- **Proposed resolution**: Update this existing assertion to expect rc 3, BAIL_REASON=ci-fix-exhausted, BAIL_NEEDS_USER_INPUT=false, and keep rebase-storm coverage on exit 4

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-ci-log-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2567-2693; python/ci_monitor.py:1021-1064
- **Concern**: Plan routes generic outer-loop exhaustion to ci-fix-exhausted even when no fix ran. Scenario: If gh-run-logs/read_failed_jobs stay in progress, callers skip vendor dispatch and then hit the shared max-retries terminal; proposed exit-3/NEEDS_USER_INPUT would launch main-agent CI fix without ready logs or failed jobs
- **Proposed resolution**: Gate ci-fix-exhausted on a ready-log fix attempt actually exhausting; keep in-progress/no-dispatch exhaustion on the existing stalled/waterfall-failed path and retain or update the in-progress regression

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-regression-harness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:2356-2382; scripts/test-ship-pr-fix-loop-2632.inc.sh:292-321,324-368
- **Concern**: Plan adds new Bash regressions but omits existing old exit-4 exhaustion assertions. Scenario: The proposed ship-pr change routes CI-fix waterfall exhaustion to exit 3 with BAIL_REASON=ci-fix-exhausted, so the current fix-loop harness will still assert rc 4 and STALL_STEP=10-max-retries and fail even if the implementation is correct
- **Proposed resolution**: Update the existing exhaustion cases to expect rc 3, BAIL_REASON=ci-fix-exhausted, and BAIL_NEEDS_USER_INPUT=false; keep rebase-storm max-retries tests on rc 4

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-regression-harness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ci_monitor.py:1021-1024,1057-1064; python/test_ci_monitor.py:682-729; scripts/ship-pr.sh:2567-2569,2693
- **Concern**: Outer-exhaustion test plan does not distinguish real fixer exhaustion from logs-still-in-progress exhaustion. Scenario: A broad fix-exhausted/exit-3 change can route a CI run whose logs never became ready into autonomous main-agent fixing, even though no vendor waterfall actually exhausted on a deterministic failure
- **Proposed resolution**: Pin the no-ready-logs path as STALLED/exit 4 or track that at least one ready-log fix attempt ran before returning ci-fix-exhausted; keep/update the existing Python in-progress test and add the matching Bash all-rc3 case only if needed to guard that branch
