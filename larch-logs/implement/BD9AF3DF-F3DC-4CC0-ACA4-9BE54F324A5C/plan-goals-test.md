## Goal
Implement issue #4234: [IMPLEMENTING] [BUG] (URGENT) design-log-publish.sh: concurrent second invocation overwrites successful first run's PUBLISH_OK result, causing false failed-publish report.

## Implementation Plan
## Plan

Implement the accepted fixes with the scope reductions folded in:

- In `scripts/design-log-publish.sh`, detect the remote log branch for every `REASON`, but keep final-mode worktree creation based on `origin/<default>`.
- Add a `REASON=final` idempotent success path based on the run log tree already existing on the refreshed default branch. Do not use ancestry checks.
- In `skills/design/scripts/design-publish.sh`, make `.design-publish-result.env` write-once only for publish-tail results after `PLAN_WRITE_OK=true`. Do not preserve stale success for validation or plan-write failures.
- Protect `final-summary.md` from false `failed-publish` rewrites when an existing result env already records `PUBLISH_OK=true`.
- Serialize result-env read/write decisions with a small lock.
- In `skills/design/scripts/design-step5c.sh`, avoid file-first stale result parsing for `design-publish.sh` exit `1` and `4`.

## Files to modify/create

### UPDATED: scripts/design-log-publish.sh

- Update the stdout contract comment for `RECOVERY_BRANCH`:
  - It may appear on any `REASON` when the concurrent-worktree guard fires and the matching remote branch is known.
  - It still appears after successful push failures as today.
- Split remote branch detection from branch reuse:
  - Fetch and detect `origin/larch-log-design-$RUN_ID` for both `final` and `pause`.
  - Keep `REMOTE_BRANCH_EXISTS` for recovery output and pause no-delta logic.
  - Do not let `REMOTE_BRANCH_EXISTS=true` make final mode base the disposable worktree on `origin/$WT_BRANCH`.
- Add a `REASON=final` idempotent success check after remote detection and before the concurrent-worktree guard:
  - Best-effort fetch the default branch:
    - `git -C "$REPO_ROOT" fetch origin "$ORIGIN_DEFAULT:refs/remotes/origin/$ORIGIN_DEFAULT" >/dev/null 2>&1 || true`
  - Probe the default branch tree:
    - `git -C "$REPO_ROOT" ls-tree -r --name-only "origin/$ORIGIN_DEFAULT" -- "larch-logs/design/$RUN_ID" | grep -q .`
  - If the probe hits, emit `PUBLISH_OK=true` with empty PR fields and `exit 0`.
  - Do not require `REMOTE_BRANCH_EXISTS=true`; this must also work after `gh pr merge --squash --delete-branch`.
  - Keep the whole block gated to `[[ "$REASON" == "final" ]]`.
- In the concurrent-worktree guard:
  - Keep `emit_publish_result false`.
  - Change `RECOVERY_BRANCH` emission to depend only on `REMOTE_BRANCH_EXISTS=true`.
  - Set `_PUBLISH_META_RECOVERY_BRANCH="$WT_BRANCH"` before persisting metadata so stdout and `.design-log-publish-metadata.env` agree.
- Keep pause behavior fail-closed:
  - `pause` must not take the default-branch idempotent success path.
  - Existing pause no-delta behavior must still emit `PUBLISH_OK=false`.
- Gate worktree branch reuse to pause only:
  - Start with `WT_BASE_REF="origin/$ORIGIN_DEFAULT"`.
  - Change to `origin/$WT_BRANCH` only when `[[ "$REASON" == "pause" && "$REMOTE_BRANCH_EXISTS" == true ]]`.

### UPDATED: skills/design/scripts/design-publish.sh

- Add result-env helpers:
  - `result_env_last_value KEY`: reads the last `KEY=` line from `$RESULT_ENV`; returns nothing for missing files, non-regular files, or symlinks.
  - `result_env_publish_ok_is_true`: returns true only when the last `PUBLISH_OK=` line is exactly `true`.
  - `result_env_load_success_metadata`: when existing `PUBLISH_OK=true`, load preserved `PR_NUMBER`, `PR_URL`, and `RECOVERY_BRANCH` from `$RESULT_ENV` if present.
- Add result-env lock helpers:
  - `result_env_lock_dir` returns `${RESULT_ENV}.lock.d`.
  - Acquire with atomic `mkdir`.
  - Use a short bounded wait for an existing lock.
  - Release with `rmdir`.
  - If the lock cannot be acquired, do not perform an unlocked clobbering write. If an eligible existing success is already present, skip the write; otherwise return failure after stdout KVs have been emitted.
- Add publish-tail state:
  - Initialize `PUBLISH_RESULT_WRITE_ONCE_ELIGIBLE=false`.
  - Set it to `true` only after `PLAN_WRITE_OK=true` and only for `SESSION_ID` publish-tail handling.
  - Do not set it for validation defects, plan-write failure, or publish-skipped because `SESSION_ID` is empty.
- In `write_result_env_and_emit`:
  - Keep stdout KV emission before disk writes.
  - Serialize the disk write decision under the result-env lock.
  - Re-read `result_env_publish_ok_is_true` inside the lock.
  - If `PUBLISH_RESULT_WRITE_ONCE_ELIGIBLE=true`, current `PUBLISH_OK` is exactly `true` or `false`, and the on-disk result env already has `PUBLISH_OK=true`, skip `phase_driver_write_result_env` entirely.
  - This preserves existing `PR_NUMBER`, `PR_URL`, warnings, and all prior result fields.
  - Do not skip the write when current `PUBLISH_OK` is missing.
  - Do not skip the write when `PLAN_WRITE_OK=false`.
  - Leave symlink refusal owned by `phase_driver_write_result_env`; `result_env_publish_ok_is_true` must return false for symlinks.
- Before publish-tail deletion or rendering:
  - After `PLAN_WRITE_OK=true` and before `rm -f "$FINAL_SUMMARY_PATH"`, check `result_env_publish_ok_is_true`.
  - If true, set `PUBLISH_OK=true`, load preserved metadata, skip `render_fresh_timing_report_for_publish`, skip `rm -f "$FINAL_SUMMARY_PATH"`, and skip `design-log-publish.sh`.
  - Continue to the approved summary path. Do not render `failed-publish`.
- In the publish failure branches:
  - Before `sanitize_publish_metadata`, `run-log append-failure`, or `add_warn` for publish failure, check `result_env_publish_ok_is_true`.
  - If true, set `PUBLISH_OK=true`, load preserved metadata, and skip failure warning/report generation for this invocation.
  - Otherwise keep existing fail-closed handling.
- Before assigning `SUMMARY_OUTCOME=failed-publish`, staging `failed-publish`, or calling `render-final-summary.sh --outcome failed-publish`:
  - Re-check `result_env_publish_ok_is_true`.
  - If true, coerce `PUBLISH_OK=true`, set `SUMMARY_OUTCOME=approved`, load preserved metadata, and skip failed-publish staging/rendering.
- Keep the existing approved render and final result-env write path.
- Keep the existing result-env symlink regression behavior.

### UPDATED: skills/design/scripts/design-step5c.sh

- Extend stdout-authority fallback handling:
  - Current exit `3` already forces a guaranteed-absent primary result env so stdout wins.
  - Apply the same primary-missing fallback for `design-publish.sh` exit `1` and `4`.
- This prevents a stale `.design-publish-result.env` with `PUBLISH_OK=true` from masking a current plan-write failure or validator-defect failure.
- Keep normal file-first parsing for exit `0`.
- Keep abort behavior for exit `2` and unexpected non-zero exits unchanged.

### UPDATED: scripts/design-log-publish.md

- Update the `RECOVERY_BRANCH` output row:
  - It is emitted for `final` and `pause` when the concurrent-worktree guard fires and `REMOTE_BRANCH_EXISTS=true`.
- Document the `REASON=final` idempotent success path:
  - The script fetches `origin/<default>` best-effort.
  - If `larch-logs/design/<RUN_ID>` already exists in the default-branch tree, it emits `PUBLISH_OK=true` and exits `0`.
  - The check runs even when the remote log branch has been deleted.
- Document why the check uses `git ls-tree` instead of `merge-base --is-ancestor`:
  - Design-log PRs are squash-merged.
  - The log branch tip is not expected to remain an ancestor of the default branch.
- Document that final mode still bases its disposable worktree on `origin/<default>` even when the remote log branch exists.

### UPDATED: skills/design/scripts/design-publish.md

- Document the narrowed write-once rule:
  - Existing `PUBLISH_OK=true` protects the result env only for publish-tail results after `PLAN_WRITE_OK=true`.
  - Validation defects and plan-write failures overwrite stale success.
  - Missing current `PUBLISH_OK` does not trigger preservation.
- Document the metadata preservation rule:
  - When preservation fires, the whole file write is skipped.
  - Existing PR metadata remains authoritative.
  - Stdout still reflects the current invocation.
- Document result-env locking:
  - The lock serializes the re-read plus write decision.
  - Symlink refusal remains delegated to `phase_driver_write_result_env`.
- Document summary protection:
  - Existing `PUBLISH_OK=true` prevents failed-publish staging and failed-publish final-summary rendering for later publish-tail invocations.

### UPDATED: skills/design/scripts/design-step5c.md

- Document result parsing authority:
  - Exit `0` reads result env first with stdout fallback.
  - Exit `1`, `3`, and `4` force stdout authority to avoid stale primary result env data.
  - Exit `2` and unexpected exits still abort before normal parse.

### UPDATED: scripts/test-design-log-publish.sh

- Add final-mode concurrent guard regression:
  - Create remote `larch-log-design-<RUN_ID>` with a commit not on `origin/main`.
  - Check that branch out in another worktree.
  - Run `--reason final`.
  - Assert `PUBLISH_OK=false`.
  - Assert `RECOVERY_BRANCH=larch-log-design-<RUN_ID>`.
- Add final-mode branch-reuse regression:
  - Create remote `larch-log-design-<RUN_ID>` ahead of `origin/main` with a branch-only sentinel.
  - Run `--reason final` without triggering the idempotent default-tree success path.
  - Assert the publish worktree is based on `origin/main`, not `origin/$WT_BRANCH`.
  - Assert the final publish path does not inherit the branch-only sentinel or otherwise take the pause reuse path.
- Add squash-merge idempotent success regression:
  - Simulate a squash-style commit on `origin/main` that contains `larch-logs/design/<RUN_ID>`.
  - Delete the remote log branch to match `gh pr merge --squash --delete-branch`.
  - Leave the local `origin/main` tracking ref stale until the script fetches it.
  - Run `--reason final`.
  - Assert `PUBLISH_OK=true`.
  - Assert no new `gh pr create` or `gh pr merge` invocation occurred.
- Add pause no-delta fail-closed regression:
  - Reuse the squash-style default-branch setup.
  - Run `--reason pause`.
  - Assert `PUBLISH_OK=false`.
  - Assert the final-only idempotent success path did not fire.

### UPDATED: skills/design/scripts/test-design-publish.sh

- Add write-once failure regression:
  - Seed `$D/.design-publish-result.env` with `PUBLISH_OK=true`, `PR_NUMBER=42`, and `PR_URL=https://example.com`.
  - Run the driver with the publish stub returning `PUBLISH_OK=false`.
  - Assert driver exits `0`.
  - Assert the result env still contains `PUBLISH_OK=true`.
  - Assert no `PUBLISH_OK=false` line was written.
  - Assert `PR_NUMBER=42` and `PR_URL=https://example.com` are preserved.
- Add true-success retry metadata preservation regression:
  - Seed existing `PUBLISH_OK=true` with PR metadata.
  - Make the publish stub return `PUBLISH_OK=true` with empty PR fields, matching the merged-default-tree idempotent path.
  - Assert the result env preserves the original PR metadata.
- Add summary protection regression:
  - Seed existing `PUBLISH_OK=true`.
  - Seed `final-summary.md` with approved content.
  - Run the driver with the publish stub returning `PUBLISH_OK=false` or non-zero.
  - Assert no `render-final-summary.sh --outcome failed-publish` call occurred.
  - Assert `final-summary.md` does not contain failed-publish content after exit.
- Add pre-publish success short-circuit regression:
  - Seed existing `PUBLISH_OK=true`.
  - Run the driver.
  - Assert `design-log-publish.sh` is not invoked.
  - Assert final summary handling remains approved.
- Add narrowed-scope stale-success regressions:
  - Seed existing `PUBLISH_OK=true`.
  - Force validator defects.
  - Assert the result env is overwritten with current validation failure state and does not preserve stale publish success.
  - Seed existing `PUBLISH_OK=true`.
  - Force plan-block write failure.
  - Assert the result env is overwritten with `PLAN_WRITE_OK=false` and does not preserve stale publish success.
- Add focused result-env lock regression:
  - Run two publish-tail invocations against the same tmpdir with deterministic stub ordering.
  - Cover success-first then failure-second: failure must re-read under the lock and skip the write.
  - Cover failure-first then success-second: final result must be success.
  - Assert the final result env never ends with `PUBLISH_OK=false` after a successful publish-tail invocation records true.
- Keep the existing symlink result-env test unchanged.

### UPDATED: skills/design/scripts/test-design-step5c.sh

- Add stale-primary regression for exit `1`:
  - Seed `.design-publish-result.env` with stale `PLAN_WRITE_OK=true` and `PUBLISH_OK=true`.
  - Stub `design-publish.sh` to emit stdout with `PLAN_WRITE_OK=false` and exit `1`.
  - Assert Step 5c parses stdout, not the stale file.
  - Assert cleanup is not eligible.
- Add stale-primary regression for exit `4`:
  - Seed `.design-publish-result.env` with stale `PLAN_WRITE_OK=true` and `PUBLISH_OK=true`.
  - Stub `design-publish.sh` to emit validator-defect stdout and exit `4`.
  - Assert Step 5c reports validator defects from stdout.
  - Assert cleanup is not eligible.

## Edge cases

- If the remote log branch was deleted after a squash merge, final-mode idempotency still works because it probes the default branch tree.
- If the default-branch fetch fails transiently, the idempotent probe may miss success and the script falls through to normal publish behavior.
- If a stale result-env lock remains from a crashed process, the writer must not perform an unlocked clobber. It either skips because existing success is visible or returns a write failure after stdout KVs.
- If a current run fails validation or plan writing after a prior success, stale `PUBLISH_OK=true` must not be preserved.
- If a publish retry reaches the publish tail before the first invocation records success, normal failure handling can still run. The late pre-summary check prevents a false failed-publish render when success appears before summary rendering.

## Failure modes

- A stale or failed `origin/<default>` fetch can delay idempotent success detection until a later retry.
- The lock cannot protect writes if callers bypass `write_result_env_and_emit`; this change keeps all driver result-env writes on that helper path.
- If stdout capture is missing on exit `1`, `3`, or `4`, `design-step5c.sh` will still fail closed rather than read stale primary success.

## Testing strategy

- Run targeted harnesses:
  - `bash scripts/test-design-log-publish.sh`
  - `bash skills/design/scripts/test-design-publish.sh`
  - `bash skills/design/scripts/test-design-step5c.sh`
- Run relevant checks:
  - `bash scripts/relevant-checks.sh`

## Acceptance

- `scripts/design-log-publish.sh` detects the remote log branch on all `REASON` values.
- Final-mode publish of a run already on `origin/<default>` emits `PUBLISH_OK=true` and exits without creating a new PR.
- Concurrent or retry `design-publish.sh` invocations do not overwrite a `.design-publish-result.env` that already holds `PUBLISH_OK=true` in the publish-tail code path.
- A concurrent second invocation that fails publish does not render `failed-publish` into `final-summary.md` when the first invocation already recorded success.
- `design-step5c.sh` reads stdout (not the stale file) when `design-publish.sh` exits `1` or `4`.
- Existing `PUBLISH_OK=true` is not preserved for validation defects or plan-write failures.
- Pause-mode behavior is unchanged.

diff_lines: 345

## Test plan
(no test plan section in plan-file)
