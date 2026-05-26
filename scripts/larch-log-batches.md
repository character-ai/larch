# larch-log-batches.sh contract

`scripts/larch-log-batches.sh` is the source of truth for larch log batch
slugs, file extensions, write modes, and sanitizer hooks.

The table intentionally covers the legacy tracking sections as durable files:
`plan-goals-test`, optional `include-probe-evidence` (redacted Phase 1 probe transcripts when plans require them), per-run setup/implementation artifacts (`parent-issue`,
`pre-review-head`, `pre-review-untracked`, `codex-impl-transcript`,
`codex-impl-transcript-meta`,
`codex-impl-transcript-prompt`, `codex-commit-message`,
`codex-impl-manifest-raw`), `plan-review-tally`, `code-review-tally`,
`review-findings-full`, review runtime batches (`review-context`,
`review-findings`, `review-panel-manifest`, `review-round-summary`,
`review-scout-manifest`, `review-tally`), `version-bump-reasoning`,
`oos-issues`, `run-statistics`, `token-report`, `timing-report`,
`execution-issues`, `final-bail-reason` (replace-mode text snapshot of the terminal `BAIL_REASON` written during `/implement` Step 18 finalize-state restore), and `session-transcript`
(the redacted Claude Code session transcript captured at Step 7a tail
pre-bump flush for full post-hoc auditability; refreshed on each CI-retry
push via `scripts/refresh-run-logs.sh`).

`plan-goals-test` uses the `plan-goals` sanitizer. The sanitizer requires a
sectioned payload with a non-empty `## Implementation Plan` body and rejects
pointer-only placeholders such as `See plan.txt`. `plan-review-tally` and
`code-review-tally` and `review-scout-manifest` use the `json-object`
sanitizer because their files are single replace-mode JSON objects.

`review-findings`, `oos-issues`, and `execution-issues` use the `json-lines`
sanitizer because they are append-mode NDJSON batches. Every non-empty line in
the appended record file must parse as JSON before `larch-log.sh` publishes the
write; raw markdown belongs in a caller-supplied structured payload (for example
composed with `jq`) before it is passed as `--record-file`, not directly in
these batches.

Edit in sync with `scripts/larch-log.sh`, `scripts/larch-log.md`, and
`scripts/test-larch-logs-batches.sh`.

`breadcrumbs/` is intentionally not listed in this batch table. It is a
commit-only directory artifact handled by `scripts/larch-log.sh commit`, because
the four-field batch schema represents single files (`slug extension mode
sanitizer`) and cannot express a directory plus the multi-stage streaming
redaction pipeline. See `scripts/larch-log.md` for the breadcrumb commit
contract.

## Tally record schema

`plan-review-tally.json` and `code-review-tally.json` each contain one JSON
object composed by `scripts/compose-tally-record.sh`:

```json
{"schema_version":2,"phase":"plan-review","batch":"plan-review-tally","mode":"simple","rounds":0,"accepted_count":0,"rejected_count":0,"exonerated_count":0,"body":"..."}
```

The `phase` value is `plan-review` or `code-review`; `batch` is the matching
batch slug; `mode` is `simple` or `hard`; counts are non-negative integers;
`exonerated_count` must be `≤ rejected_count`; `rejected_count` counts every finding that did not meet the acceptance threshold (including split-panel and exonerated vote patterns); and
`body` holds the verbatim markdown tally prose with newlines JSON-escaped.

The `json-object` sanitizer validates these tally batches before replace writes.
`review-findings-full.jsonl` is line-delimited JSON (one finding per line, with
keys `id`, `issue_number`, `phase`, `outcome`, `schema_version`, `reviewer_slots`, `round_num`,
`category`, `prose_body`); it uses no sanitizer beyond the standard tmpdir and
secret redaction pipeline because `jq` handles JSON string escaping for each
record.

## review-scout-manifest schema

`review-scout-manifest.json` contains one JSON object summarizing the dynamic
reviewer scout for a review run:

```json
{"status":"ok","dynamic_slots":2,"manifest_basename":"scout-round2-manifest.json","yield_tsv_basename":"scout-archetype-yield.tsv"}
```

`status` is the `SCOUT_STATUS` emitted by `review-core.sh`; `dynamic_slots` is
a non-negative integer; `manifest_basename` and `yield_tsv_basename` are
basename-only references to tmpdir artifacts and may be empty strings when no
file was produced.

## oos-issues record schema

Each `larch-log.sh append --batch oos-issues --record-file F` call appends every
non-empty line from the record file as a separate record. Each line MUST be a
compact JSON object — the `json-lines` sanitizer rejects multi-line
(pretty-printed) JSON and raw markdown. Use `jq -nc` for one record per file
entry (the `-c` flag emits compact single-line output); `jq -n` without `-c`
produces multi-line pretty-printed JSON that fails the sanitizer:

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
`--arg body "$BODY"` so `jq` handles JSON string escaping (newlines, quotes,
etc.) without shell word-splitting or glob expansion. For file-backed content,
`--rawfile` is also safe.
