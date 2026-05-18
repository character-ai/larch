# refresh-execution-issues.sh

Refreshes the `larch:metadata` tracking-issue summary with the current
execution-issue count while preserving the existing metadata fields.

Usage:

```bash
refresh-execution-issues.sh --issue N --run-id ID --session-env PATH --implement-tmpdir PATH [--repo OWNER/REPO]
```

Output:

- `REFRESHED=true|false`
- `REASON=issue-not-set` when `--issue 0` is passed and the helper skips cleanly
- `ERROR=<message>` on failure
