# tracking-issue-write.sh contract

`scripts/tracking-issue-write.sh` is the outbound helper for the tracking-issue
lifecycle operations that still write directly to GitHub issues:

```text
tracking-issue-write.sh create-issue --title T --body-file F [--repo OWNER/REPO]
tracking-issue-write.sh append-comment --issue N --body-file F [--lifecycle-marker ID] [--repo OWNER/REPO]
tracking-issue-write.sh rename --issue N --state in-progress|done|stalled [--round-trip BOOL] [--repo OWNER/REPO]
tracking-issue-write.sh mark-false-positive --issue N [--repo OWNER/REPO]
```

Durable run payloads are written through `scripts/larch-log.sh`. Slim
marker-keyed tracking comments are written through
`scripts/tracking-issue-summary.sh`.

## Output

Success keys:

| Subcommand | Keys |
|---|---|
| `create-issue` | `ISSUE_NUMBER=<N>`, `ISSUE_URL=<url>` |
| `append-comment` | `COMMENT_ID=<id>`, `COMMENT_URL=<url>` |
| `rename` | `RENAMED=true\|false`, `NEW_TITLE=<title>`, optional `ROUND_TRIP_APPLIED=true\|false` |
| `mark-false-positive` | `MARKED=true\|false`, `NEW_TITLE=<title>` |

Failure envelope:

```text
FAILED=true
ERROR=<single-line message>
```

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Usage or validated-content rejection |
| 2 | `gh` failure |
| 3 | Redaction helper failure |

## Security

All outbound body and title content is composed in memory, passed through
`redact-tmpdir-paths.sh` and `redact-secrets.sh`, then sent to `gh`. Captured
`gh` stderr is also redacted before it is surfaced in `ERROR=`.

`append-comment --lifecycle-marker` accepts only `[A-Za-z0-9._:-]` and rejects
the substring `--` before synthesizing the HTML marker comment.

## Tests

`scripts/test-tracking-issue-write.sh` covers the remaining writer lifecycle:
create, append, lifecycle-marker validation, rename, false-positive title
markers, redaction, and failure envelopes.
