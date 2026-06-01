### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:15-49; scripts/ship-pr.sh:2031-2157; python/ci_monitor.py:859-963
- **Concern**: Exhaustion routing contract conflicts with planned flag/test. Scenario: The plan says push launcher and no-tier failures must stay on the stall path, but also proposes setting the ready-log dispatch flag when run_ci_fix_vendor or run_ci_fix is entered and rewrites a launcher-failure exhaustion test to expect ci-fix-exhausted. Current Bash/Python fix helpers collapse launcher and push failures into generic waterfall failures, so flag-at-entry would route carve-out failures to exit 3; preserving the carve-out would fail the planned test.
- **Proposed resolution**: Pick one predicate and encode it consistently. For minimum change, keep push launcher and no-tier failures as exit 4 by setting ci-fix-exhausted only for the intended real fixer-exhaustion class, returning or detecting distinct push/no-tier/all-launcher failure details, and aligning the Bash/Python tests with that split.

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:996-1031
- **Concern**: Upfront log reuse is not gated on ready state. Scenario: Plan says reuse the collected log for the first fix-loop iteration without requiring logs.state == ready; reusing an in_progress or error capture can defer or mis-route the first outer attempt (parity break vs Bash re-fetch at scripts/ship-pr.sh:2532-2534)
- **Proposed resolution**: Only reuse the upfront capture when logs.state == ready (and only skip the first collect_failed_logs call in that case); otherwise keep per-attempt refresh

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:996-1025
- **Concern**: Upfront log reuse is not limited to ready captures. Scenario: The plan tells `evaluate_failure` to reuse the upfront `collect_failed_logs` result on the first fix-loop iteration after skipping a blind rerun for deterministic/unreadable/cap cases. When that upfront result is `in_progress` or `error`, reusing it on iteration 1 can call `run_ci_fix` with empty/non-ready logs instead of deferring like today (per-attempt `collect_failed_logs` at ~1014). That breaks parity with Bash `gh-run-logs` rc=3 deferral and `test_evaluate_failure_in_progress_defers_launch`.
- **Proposed resolution**: Reuse the upfront capture only when `logs.state == "ready"`; otherwise leave the fix loop unchanged and call `collect_failed_logs` on the first iteration (same as later attempts). Mark Bash log reuse as optional and apply the same ready-only rule if implemented.

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-ship-pr-fix-loop-2632.inc.sh:672-684
- **Concern**: Plan re-sources a stale include whose top-level body runs every #2632 case, not just the new #3334 regressions. Scenario: Re-enabling the include under make test-ship-pr-fix-loop can force this small retry-gate PR to fix unrelated stale #2632 harness failures and add runtime, breaking the minimum-change contract
- **Proposed resolution**: Put the two #3334 rerun-gate regressions directly in scripts/test-ship-pr.sh or move them to a new tiny sourced helper with no top-level legacy invocations

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:15,47-50,68-70; scripts/test-ship-pr.sh:2356-2382
- **Concern**: Exhaustion routing conflicts for launcher failures. Scenario: The plan says push/launcher failures must remain exit 4 STALLED, but also rewrites vendor_loop_ci_fix_exhausted to expect exit 3 ci-fix-exhausted after all launcher tiers fail. Implementers can either misroute launcher/health outages into main-agent code edits or make the planned tests fail.
- **Proposed resolution**: Make one contract. For the safer minimum-change path, keep launcher/push/no-tier failures on exit 4, only set the ready-log exhaustion flag after an actual code-fix attempt runs, and leave vendor_loop_ci_fix_exhausted asserting exit 4; otherwise remove the launcher-failure carveout everywhere.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2581-2693; python/ci_monitor.py:909-1064
- **Concern**: FINDING_1: Exhaustion flag is too broad for the stated stall exceptions. Scenario: The plan says push/launcher/no-tier failures must stay on the stall path, but also says to set the ready-log flag whenever run_per_job_local_fix_loop or run_ci_fix_vendor is entered. If launchers are unavailable/all fail, or _stage_and_push_ci_fixes push fails after a ready-log local fix, terminal exhaustion would see the flag and emit ci-fix-exhausted exit 3/NEEDS_USER_INPUT instead of the required exit 4/STALLED path.
- **Proposed resolution**: Track the terminal cause/status separately. Set ci-fix-exhausted only for actual fixer-attempt exhaustion after a ready-log dispatch, and explicitly keep no tiers/all tiers failed/launcher failure/push failure on existing exit_stall or Outcome.STALLED paths; add a regression for at least one launcher/push failure exception.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-dual-impl-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2581-2608; scripts/ship-pr.sh:2638-2678; python/ci_monitor.py:909-927; python/ci_monitor.py:962-964
- **Concern**: Tracking flag is specified at fixer entry, which conflicts with the promised stall path for push, launcher, and no-tier failures. Scenario: If ready logs are present but staging/push returns 1, all vendor tiers fail, or Python run_ci_fix returns waterfall-failed for no tiers or push failed, an entry-based _fix_dispatched_on_ready_log/fix_dispatched_on_ready_log makes outer exhaustion become ci-fix-exhausted/Outcome.NEEDS_USER_INPUT even though the plan says those branches stay exit 4/STALLED
- **Proposed resolution**: Revise the plan to set the exhaustion flag only from an explicit code-fix exhaustion signal and exclude push failed, no launcher tiers, and launcher-health failures; expose a separate dispatched/exhausted bool or status from the fixer if needed

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-dual-impl-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:2567-2621; python/ci_monitor.py:1014-1024
- **Concern**: Bash does not special-case ci-failed-jobs in-progress while Python does. Scenario: If gh-run-logs is rc0 but ci-failed-jobs.sh returns rc3, proposed Bash tracking keyed on gh_logs_rc==0 can fall through to run_ci_fix_vendor, while Python jobs_state == in_progress backs off before run_ci_fix; exhaustion can exit 3 in Bash and STALLED in Python
- **Proposed resolution**: Add a Bash ci_failed_rc == 3 branch matching Python jobs_state == in_progress: no fixer dispatch, no ready-log dispatch flag, backoff/continue, plus a parity regression test

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-test-plan-gaps
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr-fix-loop-2632.inc.sh:292-367,646-684; scripts/test-ship-pr.sh:3442-3448
- **Concern**: Plan re-sources a legacy include whose top-level body runs old #2632 exhaustion cases. Scenario: The new source step will run t5/t6/t21; t5 and t6 still assert rc 4 after ready-log vendor exhaustion, conflicting with the planned exit 3 ci-fix-exhausted contract and making make test-ship-pr-fix-loop fail
- **Proposed resolution**: Minimum-change fix: add the two #3334 rerun-gate regressions inline in scripts/test-ship-pr.sh instead of sourcing the whole include, or guard the include auto-run block and update any retained ready-log exhaustion cases to the new exit-3 contract
