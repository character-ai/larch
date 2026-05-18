# refresh-execution-issues.sh

Refreshes the `larch:metadata` tracking-issue summary with the current
execution-issue count while preserving the existing metadata fields.

Usage:

```bash
refresh-execution-issues.sh --implement-tmpdir PATH
```

All session state is read from files under `IMPLEMENT_TMPDIR` rather than
CLI arguments to reduce non-determinism and context bloat:

- `parent-issue.md` → `ISSUE_NUMBER`, `RUN_ID`
- `session-env.sh` → `REPO`, `AGENT`, `CODER`

Output:

- `REFRESHED=true|false`
- `REASON=issue-not-set` when no tracking issue is set (skips cleanly)
- `ERROR=<message>` on failure
