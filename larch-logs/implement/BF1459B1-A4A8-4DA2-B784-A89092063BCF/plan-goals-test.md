## Goal
Remove LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR bypass and restore unconditional post-sentinel commit rejection

## Implementation Plan
Fix #2552: Remove LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR post-merge commit bypass

Objective: Remove the post-merge git commit introduced by PR #2530 from run_postmerge_phase, restore unconditional post-sentinel rejection in larch-log.sh, invert tests that locked in the broken behavior, update docs, and add a NEVER rule.


### File changes

**1. scripts/larch-log.sh** (commit subcommand guard, ~lines 459-481)
Delete the `postmerge_ship_pr_flush` bypass block entirely. Restore unconditional
rejection: when `$IMPLEMENT_TMPDIR/post-merge-sentinel` exists, always exit 1.
The branch-is-default guard and REPO_ROOT check move up unconditionally.

**2. scripts/ship-pr.sh**
a) Lines 1694-1698: Replace the comment that references the bypass with a simpler
   "update manifest in place; no post-merge git commit" comment.
b) Lines 1772-1781: Delete the entire post-merge `larch-log.sh commit` block
   (the `if [ "${LARCH_NO_LOGS_COMMIT:-...}" != "true" ]...` block).

**3. scripts/test-ship-pr.sh** — invert three assertions:
a) `postmerge manifest finalization` (~line 1354): Change expected ordering from
   [manifest, write-final-report, commit] to [manifest, write-final-report].
   Remove the `LARCH_LOG_ARGS=commit` grep assertion.
b) `larch_log_stub_postmerge_commit_guards` (~line 1399-1426): The second sub-test
   (bypass allows commit with `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1`) should now
   assert that commit is still rejected (exit 1) even with the env var set, because
   the stub no longer honors the bypass.
c) `postmerge missing-manifest recovery` (~line 1483): Remove `LARCH_LOG_ARGS=commit`
   grep assertion and change expected ordering to [init, manifest, manifest, write-final-report].
d) Add new positive test: after run_postmerge_phase with PR_CLOSED=true, confirm
   `git rev-list --count origin/main..HEAD` is `0` (no orphan commit on local main).

**4. scripts/larch-log.md** (~lines 39-43)
Delete the "Exception" sentence about the bypass.

**5. scripts/ship-pr.md** (~lines 3, 19, 75, 91)
Remove all references to `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR` bypass, "the only
intentional exception", and scoped post-merge log commits.

**6. skills/implement/SKILL.md** — add NEVER #19
After NEVER #18, insert NEVER #19 forbidding post-merge log commits. Reference
#2182 and this issue.

**7. Cross-references** (docs/larch-log.md, docs/ship-pr.md)
Point readers at the new NEVER #19 rule.

### Testing strategy
- Run `make test-ship-pr` to verify all three inverted assertions pass.
- Run `make test-larch-log` to verify the existing sentinel-rejection test still passes
  (it was always testing unconditional rejection and should be unaffected).
- Run `/relevant-checks` for linting.

## Test plan
(no test plan section in plan-file)
