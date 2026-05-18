# write-rejected-findings.sh

Summarizes `$IMPLEMENT_TMPDIR/rejected-findings.md` without reprinting the full
findings body into the orchestrator transcript.

Usage:

```bash
write-rejected-findings.sh --implement-tmpdir PATH [--run-id ID --log-root PATH]
```

Output:

- `REJECTED_COUNT=<N>`
- `STATUS=ok|empty|failed`
- `ERROR=<message>` on usage failure
