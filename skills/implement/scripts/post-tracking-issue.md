# post-tracking-issue.sh

Publishes the Step 0.5 `larch:metadata` tracking-issue summary.

Usage:

```bash
post-tracking-issue.sh --implement-tmpdir PATH [--issue-number N] [--adopted true|false]
```

All session state is read from files under `IMPLEMENT_TMPDIR` rather than
CLI arguments to reduce non-determinism and context bloat:

- `parent-issue.md` → `ISSUE_NUMBER`, `RUN_ID` (when `--issue-number` absent)
- `session-env.sh` → `REPO`, `AGENT`, `CODER`
- `session-id` → `RUN_ID` fallback when `parent-issue.md` is absent

When `--issue-number N` is provided, `N` is used directly for `ISSUE_NUMBER`
and `parent-issue.md` is written after a successful metadata post (with
`ISSUE_NUMBER`, `RUN_ID`, and `ADOPTED=$adopted`). This co-locates the
sentinel write with confirmed success, so the file is never present without
a confirmed `larch:metadata` comment.

When `--issue-number` is absent, the script reads `ISSUE_NUMBER` from the
existing `parent-issue.md` (Branch 1 resume path — sentinel already present).

`--adopted` defaults to `true` and is only meaningful when `--issue-number`
is provided.

Output:

- `POSTED=true|false`
- `COMMENT_URL=<url-or-empty>`
- `ERROR=<message>` on failure

The script writes `summary-metadata.md` under `IMPLEMENT_TMPDIR` and calls
`scripts/tracking-issue-summary.sh upsert-summary` with the
`<!-- larch:metadata v1 runid=<R> -->` marker.
