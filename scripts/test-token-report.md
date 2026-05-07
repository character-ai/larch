# test-token-report.sh

**Purpose**: Offline regression harness for `scripts/token-report.sh`.

It uses fixture ledger + Claude transcript JSONL files to assert terse output, the full markdown multi-table shape, per-vendor headings, dropped legacy columns, the anchored old `| N/A |` cell-shape check, grand-total counts derived from fixture vendor content, `--output`, graceful unavailable output, and idempotent `## Token Report` sentinel replacement after repeated refreshes. It also covers pipe-and-newline injection fixtures for table-cell sanitization and smoke-tests an oversized existing `run-statistics.md` fixture with per-heading verification so sentinel replacement remains parser-safe.

Run via `make test-token-report` or the shard that includes it.

Update this harness when report columns, sentinel comments, source-resolution test hooks, or failure-mode wording changes.
