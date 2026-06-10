# larch-log-batches.sh contract

`scripts/larch-log-batches.sh` is the source of truth for larch log batch
slugs, file extensions, write modes, and sanitizer hooks.

The table intentionally covers the legacy tracking sections as durable files:
optional `include-probe-evidence` (redacted Phase 1 probe transcripts when plans require them), per-run setup/implementation artifacts (`parent-issue`,
`pre-review-head`, `pre-review-untracked`, `codex-impl-transcript`,
`codex-impl-transcript-meta`,
`codex-impl-transcript-prompt`, `codex-commit-message`,
`codex-impl-manifest-raw`), `plan-review-tally`, `code-review-tally`,
`review-findings-full`, review runtime batches (`review-context`,
`review-findings`, `review-panel-manifest`, `review-round-summary`,
`review-scout-manifest`, `review-tally`,
`review-findings-classification-round-1` through
`review-findings-classification-round-5`), `version-bump-reasoning`,
`oos-issues`, `run-statistics`, `token-report`, `timing-report`,
`execution-issues`, `final-bail-reason` (replace-mode text snapshot of the terminal `BAIL_REASON` written during `/implement` Step 18 finalize-state restore), and `session-transcript`
(the redacted Claude Code session transcript captured at Step 7a tail
pre-bump flush for full post-hoc auditability; refreshed on each CI-retry
push via `scripts/refresh-run-logs.sh`).

`plan-review-tally` and
`code-review-tally` and `review-scout-manifest` use the `json-object`
sanitizer because their files are single replace-mode JSON objects.
`review-findings-classification-round-N` batches are replace-mode `.tsv`
artifacts with no sanitizer beyond the standard tmpdir and secret redaction
pipeline; the producer restricts vote/rating cells to documented enum tokens.

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
`exonerated_count` is always `0` (retained for schema backward compatibility); `rejected_count` counts every finding that did not meet the acceptance threshold (0 YES); non-accepted findings with ≥1 YES are `neutral`.

`body` holds verbatim markdown tally prose for `plan-review-tally`. For
`code-review-tally` the `body` field is **omitted** — the rejected-findings
prose that used to populate it is the third copy of the same data (also in
`round-N/rejected-findings-full.md` and `review-findings-full.jsonl`); no
programmatic reader consumes `body` from `code-review-tally.json`. Canonical
`code-review-tally.json` objects contain only the envelope fields
(`schema_version`, `phase`, `batch`, `mode`, `rounds`, `accepted_count`,
`rejected_count`, `exonerated_count`).

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

## vendor-failure-diagnostics batch (#3713)

The `vendor-failure-diagnostics .txt replace none` slug is the durable carrier
for vendor-agent launch failures. Producers append redacted per-slot parts via
`append_vendor_failure_diagnostics` (`scripts/lib-failed-agent-stderr-tail.sh`);
`scripts/flush-vendor-failure-diagnostics.sh` merges parts into
`vendor-failure-diagnostics.txt` and writes the batch. `replace` mode is used (not
`append`) because the helper derives the full batch from the parts set on every
flush, so repeated pre-commit flushes converge idempotently. See
`docs/vendor-agent-diagnostics-audit.md`.
## Concise prune/log audit update

The batch table includes `reviewer-prune-ledger` as a run-root TSV replace batch for implement pruning audit history. Per-round skipped, failed, and pruned-empty states remain in `prune-decision.env` rather than synthetic ledger rows.
