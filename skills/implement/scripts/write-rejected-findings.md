# write-rejected-findings.sh

Summarizes `$IMPLEMENT_TMPDIR/rejected-findings.md` without reprinting the full
findings body into the orchestrator transcript.

Usage:

```bash
write-rejected-findings.sh --implement-tmpdir PATH [--run-id ID --log-root PATH]
```

When `--run-id` and `--log-root` are provided the script copies the rejected
findings to `$LOG_ROOT/implement/$RUN_ID/rejected-findings.md`. It prefers
`$IMPLEMENT_TMPDIR/rejected-findings-full.md` (the pre-compaction full version
preserved by `emit-tally.sh`) when it is non-empty; otherwise it falls back to
`rejected-findings.md`. `REJECTED_COUNT` is derived from the same detail file
when that full artifact is present.

Output:

- `REJECTED_COUNT=<N>`
- `STATUS=ok|empty|failed`
- `ERROR=<message>` on usage failure
