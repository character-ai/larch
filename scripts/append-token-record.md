# append-token-record.sh

Normalizes token usage sidecars written by `launch-cursor-ci.sh` and `launch-codex-ci.sh` into `$IMPLEMENT_TMPDIR/token-report.ndjson`.

## Interface

```text
append-token-record.sh --input PATH --tmpdir PATH
```

The input sidecar is line-oriented `KEY=VALUE` text. Recognized keys are `TOOL`, `INPUT`, `OUTPUT`, `CACHE_READ`, `CACHE_CREATE`, `TOTAL`, and `RAW`.

## Behavior

Missing or empty sidecars are non-fatal. Passing `--input ""` is an explicit
no-op for callers that did not run a token-reporting vendor tier. When a
non-empty input path is missing and `execution-issues.md` is absent, the helper
logs the missing sidecar to stderr so a silent loss is visible in standalone
tests.

## Harness

Covered by the CI launcher harnesses and `scripts/test-ship-pr.sh`.

## Edit In Sync

Update the two CI launchers, `scripts/ship-pr.sh`, and tests when changing this sidecar grammar.
