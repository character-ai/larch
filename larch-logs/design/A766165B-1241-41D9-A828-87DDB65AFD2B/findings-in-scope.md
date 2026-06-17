### FINDING_1: Fail-closed `_run_cycle` returns must set `next_run_id=None`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Fail-closed `_run_cycle` exits must set tuple element 6 (`next_run_id`) to `None`, not only avoid KV emission. The current `wait_err` path returns `("pushed", …, run_id, …)`; `main()` advances when element 6 is truthy, so a failed CI wait after push can burn later cycles on the same run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Spell out in the plan that every terminal fail-closed return (`wait_err`, `ACTION=bail`, missing/stale `FAILED_RUN_ID`) uses `next_run_id=None` in the 7-tuple

### FINDING_2: Post-push `ACTION=bail` and failure-shaped wait must be handled before rebase/behind/pass/`next_run` assignment
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Parsed `ACTION=bail` and other failure-shaped post-push wait outcomes are currently parse-valid and fall through to `next_run = wait.get("FAILED_RUN_ID") or run_id` (line 428), reusing a stale run. The plan orders `ACTION=bail` and post-push fail-closed rules but not relative to existing rebase/behind/pass branches; if bail or fail-without-`FAILED_RUN_ID` handling is added only at the tail or after those branches, cycles can still advance on a stale `run_id`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit plan step: after `_wait_for_ci` succeeds, if `wait.get("ACTION") == "bail"`, return `ci-fix-exhausted` immediately, before merge/pass/rebase and before any `next_run` assignment
  - From Cursor-Pragmatic: Add an explicit step: immediately after the wait_err check (and before ACTION in {rebase,rebase_then_evaluate}, BEHIND_COUNT, pass/merge, or next_run assignment), return ci-fix-exhausted for ACTION=bail and for failure-shaped wait output without a new FAILED_RUN_ID; add a regression test stubbing ACTION=bail between wait_err and rebase branches

### FINDING_3: Submodule test must assert forbidden-path snapshot is frozen before `launch_fn`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The submodule pre-launch snapshot test should assert the forbidden set is frozen before `launch_fn`. Post-mutation `coder_forbidden_paths` can miss paths added during the fixer call (related to OOS_7 pre-tier snapshot concern).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the `.gitmodules`/submodule test, assert `coder_forbidden_paths` is captured once before launch and that snapshot (not a post-tier recompute) drives the stall
