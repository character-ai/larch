# test-token-vendor-scrapers.sh

**Purpose**: Offline regression harness for the Codex and Cursor token scrape snippets used by external launchers.

It covers Codex's last `tokens used` block selection, thousands-separator stripping, non-numeric trailing rejection, Cursor `.usage` extraction and total calculation, malformed JSON fallback, and the Cursor review launcher JSON-sidecar contract where `.result` is written back to `$OUTPUT` as plain reviewer prose while raw JSON remains at `${OUTPUT}.json`. The Cursor implement-launcher smoke sets a fake non-secret `CURSOR_API_KEY` so auth preflight does not depend on a developer keychain before the PATH-stubbed `cursor` binary runs. The implement-launcher smokes clear ambient `IMPLEMENT_TMPDIR` so the unique per-case `LARCH_TOKEN_SESSION_ID` is not overwritten by a surrounding `/implement` session. They also check for a non-empty token ledger before the `jq` row assertion so #1387 / #1382 / #1397 regressions fail with the missing-ledger cause instead of an empty-row symptom.

It also exercises an offline `scripts/token-report.sh --full --markdown` regression for Codex aggregate-only telemetry: records a vendor row with only `total` set and asserts the rendered Codex section contains the expected aggregate in the `Total` column. This regression lives in this harness rather than `scripts/test-token-report.sh` because the source of truth is the `record-vendor codex total=...` write path this harness already covers.

Run via `make test-token-vendor-scrapers` or the shard that includes it.

Update this harness when launcher scrape snippets, Cursor JSON field names, or review-output preservation behavior changes.
