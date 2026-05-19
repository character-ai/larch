# write-final-report.sh

Writes the final summary projection and posts the `larch:final-summary`
tracking-issue comment.

Usage:

```bash
write-final-report.sh --implement-tmpdir PATH [--comment-only]
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

When `--comment-only` is passed, the script still rewrites
`$IMPLEMENT_TMPDIR/summary-final.md` for the GitHub upsert payload but leaves
the tracked `larch-logs/.../final-summary.md` file untouched. `ship-pr.sh`
uses this mode immediately after PR creation so the tracking issue gets the
live PR URL without leaving a dirty run-log tree on disk.

`PR_URL` is provisional until Step 8+ writes `ship-pr-state.sh`. Before PR
creation, callers should expect `PR: N/A`. `ship-pr.sh` first uses this helper
before `create-pr.sh` so the placeholder `final-summary.md` is committed into
the PR branch, then re-runs it with `--comment-only` after PR creation to
refresh the tracking comment with the live PR URL.
