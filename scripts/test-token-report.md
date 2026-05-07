# test-token-report.sh

**Purpose**: Offline regression harness for `scripts/token-report.sh`.

It uses fixture ledger + Claude transcript JSONL files to assert terse output, full markdown shape, indented skill rows, vendor rows with Claude `N/A`, grand totals, `--output`, graceful unavailable output, and idempotent `## Token Report` sentinel replacement after repeated refreshes. It also smoke-tests an oversized existing `run-statistics.md` fixture so sentinel replacement remains parser-safe.

Run via `make test-token-report` or the shard that includes it.

Update this harness when report columns, sentinel comments, source-resolution test hooks, or failure-mode wording changes.
