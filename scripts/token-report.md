# token-report.sh

**Purpose**: Render `/implement` token-spend reports by combining Claude transcript usage with the session token ledger. The script is observability-only and is never load-bearing.

## Relationship to scripts/token-tally.md

`scripts/token-tally.sh` remains the `/research` lane-token helper. It writes explicit sidecars and can optionally render a cost column. `scripts/token-report.sh` is a separate `/implement` PoC that reads Claude transcript usage and the `token-ledger.sh` JSONL ledger. It reports tokens only, with no dollar conversion and no cache-discount weighting.

## Subcommands

- `--since-last-mark --terse` prints one line for the most recent ledger mark:
  `Step N — <name>: claude=<total> tokens (input=A cache_read=B cache_create=C output=D); vendor=<sum> (codex=X, cursor=Y)`.
- `--full --markdown [--output FILE]` renders a markdown table grouped by step with indented skill rows and vendor rows.
- `--append-run-statistics FILE` renders the full table and idempotently replaces or appends a sentinel-bracketed block in `FILE`:

```
<!-- token-report-begin -->
## Token Report

...
<!-- token-report-end -->
```

`--ledger`, `--transcript`, and `--session-dir` are test hooks. Production calls resolve the ledger through `token-ledger.sh dump` and the transcript through `token-claude-source.sh`.

## Cross-cutting Failure Mode

Token reporting must never block `/implement`.

- `token-report.sh`: prints `Token report unavailable: <reason>` to stdout and exits 0.
- `token-ledger.sh`: warns on stderr and exits 0.
- `token-claude-source.sh`: prints `STATUS=unavailable` / `REASON=<msg>` to stdout and exits 1.
- Launcher scrape blocks: silent on failure; diagnostics stay in sidecars or stderr and never pollute launcher stdout.

## Table Shape

The markdown table uses compact columns: step, skill, Claude input/cache/output totals, Claude total, and vendor total. Step rows contain folded vendor totals; vendor detail rows are indented below the step with Claude columns set to `N/A`. The footer row is a grand total across all steps.

## Test Harness

`scripts/test-token-report.sh` owns fixture ledger + transcript cases, missing-source graceful output, sentinel replacement idempotency, hydrated prior-report replacement, and an oversized-report smoke case.
