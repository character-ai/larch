# write-final-report.sh

Writes the final summary projection and posts the `larch:final-summary`
tracking-issue comment.

Usage:

```bash
write-final-report.sh --implement-tmpdir PATH
```

All session state is read from files under `IMPLEMENT_TMPDIR` rather than
CLI arguments to reduce non-determinism and context bloat:

- `parent-issue.md` → `ISSUE_NUMBER`, `RUN_ID`
- `session-env.sh` → `REPO`
- `ship-pr-state.sh` → `PR_URL`, `STALL_TRACKING`

Output:

- `COMMENT_URL=<url-or-empty>`
- `STATUS=ok|skipped|failed`
- `ERROR=<message>` on failure

`STATUS=skipped` is reserved for `ISSUE_NUMBER=0` (no tracking issue). GitHub
upsert failures emit `STATUS=failed` and return non-zero.

The script writes both `$IMPLEMENT_TMPDIR/summary-final.md` and
`$IMPLEMENT_TMPDIR/larch-logs/implement/<RUN_ID>/final-summary.md`.

`/implement` calls this once during the Step 7a pre-bump log flush, before
`ship-pr.sh` can write the post-merge sentinel that suppresses new log commits.
That pre-merge projection may not include the eventual merge SHA, but it is the
copy that rides inside the PR's committed run-log. The later Step 17/18 calls
remain best-effort refreshes for stalled or non-merged paths.
