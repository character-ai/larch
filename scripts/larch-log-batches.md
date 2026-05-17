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
pointer-only placeholders such as `See plan.txt`. `plan-review-tally` and
`code-review-tally` use the `json-object` sanitizer because their files are
single replace-mode JSON objects.

`review-findings`, `oos-issues`, and `execution-issues` use the `json-lines`
sanitizer because they are append-mode NDJSON batches. Every non-empty line in
the appended record file must parse as JSON before `larch-log.sh` publishes the
write; raw markdown belongs in a caller-supplied structured payload (for example
composed with `jq`) before it is passed as `--record-file`, not directly in
these batches.

Edit in sync with `scripts/larch-log.sh`, `scripts/larch-log.md`, and
`scripts/test-larch-logs-batches.sh`.

## Tally record schema

`plan-review-tally.json` and `code-review-tally.json` each contain one JSON
object composed by `scripts/compose-tally-record.sh`:

```json
{"schema_version":1,"phase":"plan-review","batch":"plan-review-tally","mode":"simple","rounds":0,"accepted_count":0,"rejected_count":0,"body":"..."}
```

The `phase` value is `plan-review` or `code-review`; `batch` is the matching
batch slug; `mode` is `simple` or `hard`; counts are non-negative integers; and
`body` holds the verbatim markdown tally prose with newlines JSON-escaped.

The `json-object` sanitizer validates these tally batches before replace writes.
`review-findings-full.md` is raw markdown and uses no sanitizer beyond the
standard tmpdir and secret redaction pipeline.

## oos-issues record schema

Each `larch-log.sh append --batch oos-issues --record-file F` call writes one
record to the batch. The record file MUST contain exactly one non-empty line
that is a compact JSON object — the `json-lines` sanitizer rejects multi-line
(pretty-printed) JSON and raw markdown. Use `jq -nc` (the `-c` flag emits
compact single-line output); `jq -n` without `-c` produces multi-line
pretty-printed JSON that fails the sanitizer:

```bash
jq -nc --arg phase "code-review" --arg body "<sanitized markdown>" \
    '{"phase":$phase,"step":"9a.1","category":"OOS","body":$body}' \
    > "$OOS_RECORD_FILE"
```

Record fields: `phase` (pipeline phase, e.g. `"code-review"` or `"implement"`),
`step` (`"9a.1"`), `category` (`"OOS"`), `body` (sanitized markdown string;
apply secrets → `<REDACTED-TOKEN>`, internal URLs → `<INTERNAL-URL>`, PII →
`<REDACTED-PII>` before passing to `--arg body`).

Compose the body in a shell variable or temp file first, then pass via
`--arg body` so `jq` handles JSON string escaping (newlines, quotes, etc.).
