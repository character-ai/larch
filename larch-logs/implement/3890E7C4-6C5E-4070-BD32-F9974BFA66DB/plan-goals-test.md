## Goal
Fix committed final-summary.md showing OUTCOME=bailed after successful merge by adding post-merge write-final-report.sh + larch-log commit in run_postmerge_phase

## Implementation Plan

### Problem
`write-final-report.sh` is called in `run_pr_create_phase` (ship-pr.sh Phase=pr-create) BEFORE the PR is merged, so `MERGE_RESULT` is empty and `OUTCOME=bailed` is written to `final-summary.md`. After the merge, `MERGE_RESULT=merged` is set in `ship-pr-state.sh`, but no subsequent call updates the committed `final-summary.md`. `refresh-run-logs.sh` intentionally short-circuits on post-merge state to avoid pushing commits to deleted branches. The audit reads the committed file from the git repo, so it always sees `OUTCOME=bailed`.

### Fix
In `scripts/ship-pr.sh`, `run_postmerge_phase()`, after the existing manifest-update if-block (which guards on `flush_run_id` non-empty, `pr_num` non-empty, `REPO_UNAVAILABLE=false`, and `PR_CLOSED=true`), add:
1. Best-effort `write-final-report.sh --implement-tmpdir "$IMPLEMENT_TMPDIR"` call (without `--comment-only`) — this updates `final-summary.md` in the tmpdir with the correct `OUTCOME=merged` (reading `MERGE_RESULT` from `ship-pr-state.sh`) and also refreshes the tracking-issue comment.
2. If `LARCH_NO_LOGS_COMMIT != true`, call `larch-log.sh commit` to commit the updated `final-summary.md` to the current branch (main after local-cleanup).
3. Both calls use `record_failure` on non-zero exit (best-effort).

### Files to modify
- `scripts/ship-pr.sh`: Add post-merge `write-final-report.sh` + `larch-log.sh commit` in `run_postmerge_phase`
- `scripts/ship-pr.md`: Update the "Postmerge Phase" section to reflect the new final-summary flush

### Exact location in ship-pr.sh
Inside the `if [ -n "$flush_run_id" ] && [ -n "$pr_num" ] && [ "$(read_state REPO_UNAVAILABLE)" = "false" ] && [ "$(read_state PR_CLOSED)" = "true" ]` block, after the `larch-log.sh manifest --field "status=done"` call (inside the `if [ "$recovery_ok" = "false" ]` ... `else` ... `fi` block).


## Test plan
- Check: `make test-ship-pr-postmerge` (verifies postmerge phase state transitions)
- Check: `make lint-bash32` (new shell code must be Bash 3.2 compatible)
- Check: `/relevant-checks` passes
