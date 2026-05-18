# write-final-report.sh

Writes the final summary projection and posts the `larch:final-summary`
tracking-issue comment.

Usage:

```bash
write-final-report.sh --issue N --run-id ID --pr-url URL --stall-tracking BOOL --session-env PATH --implement-tmpdir PATH [--repo OWNER/REPO]
```

Output:

- `COMMENT_URL=<url-or-empty>`
- `STATUS=ok|skipped|failed`
- `ERROR=<message>` on failure

`STATUS=skipped` is reserved for `--issue 0` (no tracking issue). GitHub
upsert failures emit `STATUS=failed` and return non-zero.

The script writes both `$IMPLEMENT_TMPDIR/summary-final.md` and
`$IMPLEMENT_TMPDIR/larch-logs/implement/<RUN_ID>/final-summary.md`.
