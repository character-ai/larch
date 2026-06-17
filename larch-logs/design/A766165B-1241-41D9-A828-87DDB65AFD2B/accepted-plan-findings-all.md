### FINDING_2: Slimmed `run_ci_fix` may leave unused compatibility parameters
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Trimming `run_ci_fix` removes the only reads of legacy parameters while preserving the existing signature. The plan keeps direct callers passing `run_id`, `repo`, `logs`, `plan_file`, `launch_fn`, and `output_dir`, but the pending-only body will not read them. `make py-lint` runs pylint, so the change can fail verification with unused-argument warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: When slimming `run_ci_fix`, either explicitly consume the now-unused compatibility parameters with `_ = ...` or narrow the signature and update every caller in the same change.


### FINDING_3: Forbidden-path guard not pinned to pre-tier snapshot
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Forbidden-path guard is not pinned to the pre-tier snapshot. If a conflict fixer edits `.gitmodules` and a submodule path, computing forbidden paths after launch can omit the original submodule path; the stall branch can also leave non-conflict deltas because the plan only resets conflict paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Capture forbidden paths and the tier baseline before each tier launch; on any forbidden touch, revert with that snapshot, revert the tier delta back to baseline, reset conflicts, then raise Stalled without handoff


### FINDING_4: Post-push CI wait without `FAILED_RUN_ID` can reuse stale `run_id`
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: After a pushed fix, parsed non-terminal CI-wait output without `FAILED_RUN_ID` is still treated as cycle progress. `_wait_for_ci` can return parse-valid output for `CI_STATUS=fail`/`failure` with any `ACTION` and no `FAILED_RUN_ID`; `_run_cycle` then sets `next_run = wait.get("FAILED_RUN_ID") or run_id` and continues with status `pushed`, so the delegated loop can burn remaining cycles against the old `run_id` without a new failing CI run, contrary to the plan's malformed-output fail-closed goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `_run_cycle` after a successful push, return `ci-fix-exhausted` (no `next_run_id`) unless wait indicates pass/merge/rebase or supplies a non-empty `FAILED_RUN_ID`. Add a stubbed `_run_cycle` test for parsed CI failure with `ACTION` set and no `FAILED_RUN_ID`
  - From Codex-Pragmatic: Require `FAILED_RUN_ID` for failure/evaluate_failure wait output, or return `ci-fix-exhausted` in `_run_cycle` when the post-push wait action needs a failed run id but it is absent; cover that stubbed case


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:266-275
- **Concern**: [SCOPE-REDUCTION] Forbidden-path guard must run before conflict staging on successful fixer tiers. Scenario: Plan says guard runs after launch and before accepting a resolved tier, but `_resolve_conflicts` calls `_stage_resolved_conflict_files` as soon as `tier_succeeded` is true. If a conflict path is `.claude-plugin/plugin.json` or another forbidden path, the guard can run too late and the forbidden file is already staged
- **Proposed resolution**: Pin the guard immediately after `launch_fn(tier)` when `tier_succeeded`, and before `_stage_resolved_conflict_files`; on any revert, reset conflict paths and raise `Stalled` without staging




### FINDING_6: Post-push failure accepts current `run_id` as progress via `FAILED_RUN_ID`
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Post-push failure accepts any non-empty `FAILED_RUN_ID` as progress, including the current run id. If `ci wait` reports `CI_STATUS=fail` with `FAILED_RUN_ID` equal to the `run_id` just fixed, the delegate will start the next cycle from the same stale run and still burns cycles despite the plan goal to advance only to a new failing run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Require FAILED_RUN_ID to be non-empty and different from the current run_id before returning pushed/next_run_id; otherwise return ci-fix-exhausted with a stable stale failed-run detail, and cover that stubbed wait case



