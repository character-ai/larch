# larch-log-batches.sh contract

`scripts/larch-log-batches.sh` is the source of truth for larch log batch
slugs, file extensions, write modes, and sanitizer hooks.

The table intentionally covers the legacy tracking sections as durable files:
`plan-goals-test`, `plan-review-tally`, `code-review-tally`,
`review-findings-full`, review runtime batches (`review-context`,
`review-findings`, `review-panel-manifest`, `review-round-summary`,
`review-tally`), `version-bump-reasoning`, `oos-issues`, `run-statistics`,
`token-report`, `timing-report`, `execution-issues`, and `session-transcript`
(the redacted Claude Code session transcript captured at Step 18 for full
post-hoc auditability).

`plan-goals-test` uses the `plan-goals` sanitizer. The sanitizer requires a
sectioned payload with a non-empty `## Implementation Plan` body and rejects
pointer-only placeholders such as `See plan.txt`.

Edit in sync with `scripts/larch-log.sh`, `scripts/larch-log.md`, and
`scripts/test-larch-logs-batches.sh`.

## Tally record schema

`plan-review-tally.ndjson` and `code-review-tally.ndjson` use one JSON object
per line. Records are composed by `scripts/compose-tally-record.sh`:

```json
{"schema_version":1,"phase":"plan-review","batch":"plan-review-tally","mode":"simple","rounds":0,"accepted_count":0,"rejected_count":0,"body":"..."}
```

The `phase` value is `plan-review` or `code-review`; `batch` is the matching
batch slug; `mode` is `simple` or `hard`; counts are non-negative integers; and
`body` holds the verbatim markdown tally prose with newlines JSON-escaped.

The `json-lines` sanitizer validates these tally batches and
`review-findings-full.ndjson` before append. Empty append payloads are accepted
as no-op files; every non-empty line must parse as JSON.
