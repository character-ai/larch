## Proposed Design Outline

### Goals
- Fix false `failed-publish` summary: a concurrent second `design-step5c.sh` invocation must not overwrite a successful `.design-publish-result.env` with `PUBLISH_OK=false`.
- Add `RECOVERY_BRANCH` emission for all `REASON` values (not just `pause`) when the concurrent-guard fires.
- Add idempotency: if the log branch is already merged into the default branch, treat the publish as already done and return `PUBLISH_OK=true`.

### Non-goals
- Do not change the CI wait loop, worktree creation logic, or push/merge flow.
- Do not serialize concurrent `design-step5c.sh` invocations.
- Do not change behavior for `REASON=pause` beyond adding the merged-branch early-exit.

### Approach sketch
- In `scripts/design-log-publish.sh`: move the `REMOTE_BRANCH_EXISTS` fetch+show-ref block outside the `REASON==pause` gate so it always runs (RC-2 partial).
- In `scripts/design-log-publish.sh`: after the fetch, check `git merge-base --is-ancestor origin/$WT_BRANCH origin/$ORIGIN_DEFAULT`; if true, emit `PUBLISH_OK=true` and exit 0 (RC-3).
- In `scripts/design-log-publish.sh`: remove the `REASON==pause` condition from the `RECOVERY_BRANCH` emission so it fires whenever `REMOTE_BRANCH_EXISTS=true` (RC-2 final).
- In `skills/design/scripts/design-publish.sh` `write_result_env_and_emit`: add a write-once guard that skips writing to `$RESULT_ENV` when the file already contains `PUBLISH_OK=true` and the new result is `PUBLISH_OK!=true` (RC-1).
- Update `scripts/design-log-publish.md` to document `RECOVERY_BRANCH` emission on concurrent-final path.

### Surfaces in scope
- `scripts/design-log-publish.sh` — lines 241–255 (concurrent-guard block)
- `skills/design/scripts/design-publish.sh` — `write_result_env_and_emit` function
- `scripts/design-log-publish.md` — RECOVERY_BRANCH output contract

### Open questions
- None.
