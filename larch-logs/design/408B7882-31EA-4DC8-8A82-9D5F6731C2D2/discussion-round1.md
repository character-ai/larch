## Decision 1: Fix layer
- **Question**: Where does the fix live — narrow (`run_per_job_local_fix_loop` in `ship-pr.sh`) or broad (`lint-fix-loop.sh:322` head-changed handling)?
- **Resolution**: Broad — modify `lint-fix-loop.sh` so `head-changed-after-dispatch` emits `LINT_FIX_STATUS=applied` with delta paths derived from `git diff --name-only baseline_head..current_head` and `LINT_FIX_COMMIT_SHA` set to the coder's new HEAD. Both callers (`run_per_job_local_fix_loop` at ship-pr.sh:1863 and `run_checks_with_lint_fix_loop` at ship-pr.sh:1087) inherit the fix through the existing `applied` path without touching `_rcc_handle_fix_status`.
- **Source**: user

## Decision 2: Forbidden-path safety on coder commits
- **Question**: Should the fix extend forbidden-path enforcement to inspect commit content (since `post_dispatch_forbidden_revert` only handles working-tree changes)?
- **Resolution**: Yes — when HEAD changed after dispatch, diff `baseline_head..current_head --name-only` against `forbidden_paths_file`. If any forbidden path appears in the commit content, `git reset --hard "$baseline_head"` to discard the coder's commit and emit `LINT_FIX_STATUS=failed FAILURE_REASON=forbidden-path-violation` (matching the existing working-tree revert's failure status). This preserves the submodule-prohibition invariant.
- **Source**: user

## Decision 3: Scope confined to lint-fix-loop layer
- **Question**: Does the fix touch `ship-pr.sh` (`_rcc_handle_fix_status`, `run_per_job_local_fix_loop`, `run_checks_with_lint_fix_loop`)?
- **Resolution**: No — Decision 1 chooses the broad fix at the lint-fix-loop layer. ship-pr.sh's `_RCC_STATUS=head-changed` branch in `_rcc_handle_fix_status` becomes unreachable on the success path but stays as a defensive fallback (no removal in this PR). Other call sites that read `LINT_FIX_STATUS=applied` already handle commits correctly (`_stage_and_push_ci_fixes` re-runs `git-push.sh` on already-committed HEAD with no staged delta, which is the desired no-op-then-push behavior).
- **Source**: codebase

## Decision 4: Test surface
- **Question**: Which regression tests need updating?
- **Resolution**: Two updates plus one new positive case:
  - `scripts/test-lint-fix-loop.sh` case1 (line 137-142): change assertion from `LINT_FIX_STATUS=failed FAILURE_REASON=head-changed-after-dispatch` to `LINT_FIX_STATUS=applied LINT_FIX_COMMIT_SHA=<new HEAD>`.
  - `scripts/test-ship-pr.sh` (line 3280-3304): the "per-job head-changed exits through stall recovery" case must invert — head-changed should now flow through `_stage_and_push_ci_fixes` + `ci-wait.sh`, not `exit_stall 10-head-changed`. Either delete the case or rewrite to assert the new push-and-rerun path.
  - Add a new `test-lint-fix-loop.sh` case that exercises the forbidden-path-in-commit branch (coder commits a submodule path → expect `LINT_FIX_STATUS=failed FAILURE_REASON=forbidden-path-violation` and HEAD reset to baseline).
- **Source**: codebase

## Decision 5: Documentation update
- **Question**: Does `scripts/lint-fix-loop.md` need updating for the behavior change?
- **Resolution**: Yes — sibling doc must describe the new applied-with-coder-commit semantics and the commit-content forbidden-path enforcement. Per `.claude/rules/script-md-siblings.md`, the `.md` is updated in the same PR as the `.sh` behavior change.
- **Source**: codebase
