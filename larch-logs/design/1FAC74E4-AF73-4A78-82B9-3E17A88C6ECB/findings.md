### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_agentic_fix.py:66-82
- **Concern**: Per-cycle CI run id is not rebound after passive wait. Scenario: The loop body reads failed jobs/logs via read_failed_jobs(run_id=...) and collect_failed_logs(run_id=...) using the initial --run-id for every cycle. After a push, GitHub starts a new workflow run; the edge case calls for continuing from the new failed run id, but the loop steps never parse FAILED_RUN_ID from ci wait output (or poll_ci) and rebind run_id before the next cycle. Cycle 2+ can target the pre-push run and fix the wrong logs or stall.
- **Proposed resolution**: After each blocking ci wait, parse FAILED_RUN_ID (and bail if missing while CI is still failing). Update the in-loop run_id before read_failed_jobs, collect_failed_logs, and the next Claude launch.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:1424-1440
- **Concern**: Agentic delegate launch omits git working-tree cwd contract. Scenario: `evaluate_failure` will subprocess `ci agentic-fix` but the plan never requires `runner.run(..., cwd=repo_root)` or a `--repo-root` argv; `RunContext.repo` is the GitHub slug, not a filesystem path, so git/verify/push inside the delegate can run in the wrong directory
- **Proposed resolution**: Document and implement that `evaluate_failure` passes the parent `cwd` into the subprocess invocation (or add `--repo-root` to `ci agentic-fix` and thread it through every git call)

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:1424-1440
- **Concern**: The agentic delegate argv contract omits repo working-tree cwd even though evaluate_failure and monitor already receive cwd=repo_root from ship.py.. Scenario: Spawning python/cli.py ci agentic-fix without cwd=repo_root (or an explicit --cwd/--repo-root flag) makes git reads, launch_tier, verify_job_locally, and stage_and_push run against the wrong directory when the parent process cwd differs.
- **Proposed resolution**: Add --cwd (or --repo-root) to the ci agentic-fix CLI surface, thread evaluate_failure's cwd into the subprocess invocation, and assert in test_ci_monitor.py that runner.run uses the same cwd the in-process path used today.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_agentic_fix.py:66-78
- **Concern**: The per-cycle body says not to push when local verification fails but does not require reverting that cycle's working-tree delta before continuing.. Scenario: Failed verify leaves dirty edits in the tree; the next cycle captures a polluted baseline, HEAD/submodule/forbidden guards can mis-classify, and a later cycle may push a bundle that still fails the original job.
- **Proposed resolution**: State explicitly in the NEW module steps: on verify_job_locally failure, revert the cycle delta with the same baseline tracked/untracked sets used for forbidden-path rollback, then continue or exhaust; add a test_ci_agentic_fix.py case that fails verify on cycle 1, mutates nothing lasting, and succeeds on cycle 2.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:1566-1572
- **Concern**: Replacing run_ci_fix with agentic KV mapping drops the code_fix_attempted_on_ready_log to fix-exhausted promotion for local-unfixable outcomes.. Scenario: Today, when fixers run but jobs are later deemed unfixable (toolchain/prepare_python_toolchain path), evaluate_failure returns fix-exhausted with the ci-fix-exhausted detail prefix; the plan maps agentic STATUS=local-unfixable straight to NEEDS_USER_INPUT, changing operator routing and stall detail.
- **Proposed resolution**: Either emit a distinct agentic status (or DETAIL flag) when fix was attempted before local-unfixable, or have evaluate_failure promote local-unfixable to fix-exhausted using the same code_fix_attempted_on_ready_log rule; extend test_ci_monitor.py to cover post-attempt unfixable parity with evaluate_failure_exhausted_routes_needs_user_input.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rebase.py:240-289
- **Concern**: [SCOPE-REDUCTION] The plan reimplements the entire run_waterfall tier loop inline instead of extending run_waterfall with a small post-success hook for driver staging and unmerged-path verification.. Scenario: A second copy of first-tier short-circuit, health continuation, and paths_delta_revert logic will drift from agents.run_waterfall (already covered by test_agents.py), producing conflict-resolution behavior that diverges from CI/lint fixer semantics after future waterfall tweaks.
- **Proposed resolution**: Prefer extending run_waterfall with optional on-success staging plus unmerged-path gating (continue to next tier when markers remain), and keep rebase.py diff limited to removing bump prepass plus wiring the hook; retain the new staging tests without duplicating the full loop body.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_agentic_fix.py:66-79
- **Concern**: Agentic cycle omits delta path computation before stage_and_push. Scenario: The plan captures baseline tracked/untracked sets and calls ci_monitor.stage_and_push after verification, but never computes changed paths via ci_monitor._delta_paths (or equivalent). stage_and_push only commits when delta_paths is non-empty, so a successful Opus edit plus passing local verify would still return push failed with no commit
- **Proposed resolution**: After verification passes, compute delta_paths from the pre-cycle baselines (same contract as ci_monitor.run_ci_fix today), pass them into stage_and_push with commit_label claude, and treat empty delta as a no-progress cycle outcome

### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py; python/ci_agentic_fix.py; docs/external-reviewers.md; SECURITY.md
- **Concern**: Plan drops Codex/Cursor from ship-pr CI fixing despite the scoped Claude → Codex → Cursor waterfall policy. Scenario: The requested ship-pr fixer order keeps Codex gpt-5.5 and Cursor composer-2.5 after Claude, but the plan says role=fix stops using them and documents no fallback, so CI-fix behavior no longer matches the specified order/model policy
- **Proposed resolution**: Revise the CI agentic delegate to honor config.FIXER_TIER_ORDER for ship-pr CI fixes, with Claude/Opus first and Codex/Cursor fallback semantics preserved unless the feature scope is explicitly narrowed

### OOS_1:
- **Description**: The plan updates stall-recovery-report.sh retry_cap_for but not the sibling stall-recovery-report.md table that still documents ci-fix-exhausted max attempts as 8.. Scenario: Operators reading the .md contract get stale retry guidance after Python/bash classifiers move ci-fix-exhausted to cap 0.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/stall-recovery-report.md:201
- **Phase**: design
