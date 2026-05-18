# post-tracking-issue.sh

Publishes the Step 0.5 `larch:metadata` tracking-issue summary.

Usage:

```bash
post-tracking-issue.sh --issue N --run-id ID --session-env PATH [--agent claude] [--coder claude] [--repo OWNER/REPO]
```

Output:

- `POSTED=true|false`
- `COMMENT_URL=<url-or-empty>`
- `ERROR=<message>` on failure

The script writes `summary-metadata.md` beside `--session-env` and calls
`scripts/tracking-issue-summary.sh upsert-summary` with the
`<!-- larch:metadata v1 runid=<R> -->` marker.
