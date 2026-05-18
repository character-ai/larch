# refresh-execution-issues.sh

Refreshes the `larch:metadata` tracking-issue summary with a lightweight count
of pending `execution-issues.md` entries.

Usage:

```bash
refresh-execution-issues.sh --issue N --run-id ID --session-env PATH --implement-tmpdir PATH [--repo OWNER/REPO]
```

Output:

- `REFRESHED=true|false`
- `ERROR=<message>` on failure
