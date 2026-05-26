# test-token-vendor-scrapers.sh

**Purpose**: Offline regression harness for the Codex and Cursor token scrape snippets used by external launchers.

It covers Codex `--json` usage parsing through `scripts/parse-codex-usage.sh`, Cursor `.usage` extraction and total calculation, malformed JSON fallback, and the Cursor review launcher JSON-sidecar contract where `.result` is written back to `$OUTPUT` as plain reviewer prose while raw JSON remains at `${OUTPUT}.json`. The Cursor implement-launcher smoke sets a fake non-secret `CURSOR_API_KEY` so auth preflight does not depend on a developer keychain before the PATH-stubbed `cursor` binary runs. The implement-launcher smokes clear ambient `IMPLEMENT_TMPDIR` so the unique per-case `LARCH_TOKEN_SESSION_ID` is not overwritten by a surrounding `/implement` session. They also check for a non-empty token ledger before the `jq` row assertion so #1387 / #1382 / #1397 regressions fail with the missing-ledger cause instead of an empty-row symptom.

It also exercises offline `scripts/token-report.sh` and `scripts/token-cost.sh` regressions for Codex telemetry: per-bucket rows populate `BUCKETS_codex` and avoid the blended-rate warning, while a legacy aggregate-only row still renders the expected `Total` column and warning behavior.

Run via `make test-token-vendor-scrapers` or the shard that includes it.

Update this harness when launcher scrape snippets, Cursor JSON field names, or review-output preservation behavior changes.
