# test-token-vendor-scrapers.sh

**Purpose**: Offline regression harness for the Codex and Cursor token scrape snippets used by external launchers.

It covers Codex's last `tokens used` block selection, thousands-separator stripping, non-numeric trailing rejection, Cursor `.usage` extraction and total calculation, malformed JSON fallback, and the Cursor review launcher JSON-sidecar contract where `.result` is written back to `$OUTPUT` as plain reviewer prose while raw JSON remains at `${OUTPUT}.json`. The Cursor implement-launcher smoke sets a fake non-secret `CURSOR_API_KEY` so auth preflight does not depend on a developer keychain before the PATH-stubbed `cursor` binary runs.

Run via `make test-token-vendor-scrapers` or the shard that includes it.

Update this harness when launcher scrape snippets, Cursor JSON field names, or review-output preservation behavior changes.
