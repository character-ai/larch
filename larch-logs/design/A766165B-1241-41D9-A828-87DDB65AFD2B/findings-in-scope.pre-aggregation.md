### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_agentic_fix.py:401-429
- **Concern**: Fail-closed `_run_cycle` exits must set tuple element 6 (`next_run_id`) to `None`, not only avoid KV emission. Scenario: Current wait-error path returns `("pushed", …, run_id, …)`; `main()` advances when element 6 is truthy, so a failed CI wait after push can burn later cycles on the same run
- **Proposed resolution**: Spell out in the plan that every terminal fail-closed return (`wait_err`, `ACTION=bail`, missing/stale `FAILED_RUN_ID`) uses `next_run_id=None` in the 7-tuple

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_agentic_fix.py:391-429
- **Concern**: `ACTION=bail` must be handled before the post-push `FAILED_RUN_ID` advance block. Scenario: Parsed bail is currently parse-valid and falls through to `next_run = wait.get("FAILED_RUN_ID") or run_id`, reusing a stale run (OOS_5)
- **Proposed resolution**: Add an explicit plan step: after `_wait_for_ci` succeeds, if `wait.get("ACTION") == "bail"`, return `ci-fix-exhausted` immediately, before merge/pass/rebase and before any `next_run` assignment

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_rebase.py:111-122
- **Concern**: Submodule pre-launch snapshot test should assert forbidden set is frozen before `launch_fn`. Scenario: OOS_7 is about pre-tier snapshot; post-mutation `coder_forbidden_paths` can miss paths added during the fixer call
- **Proposed resolution**: In the `.gitmodules`/submodule test, assert `coder_forbidden_paths` is captured once before launch and that snapshot (not a post-tier recompute) drives the stall

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_agentic_fix.py:391-429
- **Concern**: Plan orders ACTION=bail and post-push fail-closed rules but not relative to existing rebase/behind/pass branches. Scenario: Today ACTION=bail is parse-valid and falls through to next_run = FAILED_RUN_ID or run_id (line 428). If bail or fail-without-FAILED_RUN_ID handling is added only at the tail, or after rebase/behind checks, bail can still advance cycles on a stale run_id
- **Proposed resolution**: Add an explicit step: immediately after the wait_err check (and before ACTION in {rebase,rebase_then_evaluate}, BEHIND_COUNT, pass/merge, or next_run assignment), return ci-fix-exhausted for ACTION=bail and for failure-shaped wait output without a new FAILED_RUN_ID; add a regression test stubbing ACTION=bail between wait_err and rebase branches

