### [Plan Review] FINDING_1

### FINDING_1: Per-cycle CI run id not rebound after passive wait
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The agentic loop uses the initial `--run-id` for every cycle when calling `read_failed_jobs` and `collect_failed_logs`. After a push, GitHub starts a new workflow run, but the loop never parses `FAILED_RUN_ID` from `ci wait` (or `poll_ci`) output and rebinds `run_id` before the next cycle. Cycle 2+ can target the pre-push run, fixing the wrong logs or stalling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After each blocking ci wait, parse FAILED_RUN_ID (and bail if missing while CI is still failing). Update the in-loop run_id before read_failed_jobs, collect_failed_logs, and the next Claude launch.


### [Plan Review] FINDING_3

### FINDING_3: Failed local verify leaves cycle delta unreverted
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The per-cycle body says not to push when local verification fails but does not require reverting that cycle's working-tree delta before continuing. Failed verify leaves dirty edits in the tree; the next cycle captures a polluted baseline, HEAD/submodule/forbidden guards can mis-classify, and a later cycle may push a bundle that still fails the original job.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: State explicitly in the NEW module steps: on verify_job_locally failure, revert the cycle delta with the same baseline tracked/untracked sets used for forbidden-path rollback, then continue or exhaust; add a test_ci_agentic_fix.py case that fails verify on cycle 1, mutates nothing lasting, and succeeds on cycle 2.


### [Plan Review] FINDING_6

### FINDING_6: Plan drops Codex/Cursor from ship-pr CI fixing
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan drops Codex/Cursor from ship-pr CI fixing despite the scoped Claude → Codex → Cursor waterfall policy. The requested ship-pr fixer order keeps Codex gpt-5.5 and Cursor composer-2.5 after Claude, but the plan says `role=fix` stops using them and documents no fallback, so CI-fix behavior no longer matches the specified order/model policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise the CI agentic delegate to honor config.FIXER_TIER_ORDER for ship-pr CI fixes, with Claude/Opus first and Codex/Cursor fallback semantics preserved unless the feature scope is explicitly narrowed


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rebase.py:240-289
- **Concern**: [SCOPE-REDUCTION] The plan reimplements the entire run_waterfall tier loop inline instead of extending run_waterfall with a small post-success hook for driver staging and unmerged-path verification.. Scenario: A second copy of first-tier short-circuit, health continuation, and paths_delta_revert logic will drift from agents.run_waterfall (already covered by test_agents.py), producing conflict-resolution behavior that diverges from CI/lint fixer semantics after future waterfall tweaks.
- **Proposed resolution**: Prefer extending run_waterfall with optional on-success staging plus unmerged-path gating (continue to next tier when markers remain), and keep rebase.py diff limited to removing bump prepass plus wiring the hook; retain the new staging tests without duplicating the full loop body.


