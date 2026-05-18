# post-tracking-issue.sh

Publishes the Step 0.5 `larch:metadata` tracking-issue summary.

Usage:

```bash
post-tracking-issue.sh --implement-tmpdir PATH
```

All session state is read from files under `IMPLEMENT_TMPDIR` rather than
CLI arguments to reduce non-determinism and context bloat:

- `parent-issue.md` → `ISSUE_NUMBER`, `RUN_ID`
- `session-env.sh` → `REPO`, `AGENT`, `CODER`
- `session-id` → `RUN_ID` fallback when `parent-issue.md` is absent

Output:

- `POSTED=true|false`
- `COMMENT_URL=<url-or-empty>`
- `ERROR=<message>` on failure

The script writes `summary-metadata.md` under `IMPLEMENT_TMPDIR` and calls
`scripts/tracking-issue-summary.sh upsert-summary` with the
`<!-- larch:metadata v1 runid=<R> -->` marker.
