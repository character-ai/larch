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

The full markdown output renders as **one Claude table plus one table per vendor present in the run**, each preceded by an `### <vendor>` heading and a blank line. The Claude table is always emitted; vendor tables are emitted only when at least one row of that vendor exists at or after the first ledger mark.

1. **Claude** - `Step | Skill | Claude Input | Claude Output`. One step-summary row per ledger mark followed by per-skill detail rows (blank Step cell + skill identifier in the Skill column; no indentation marker, no HTML entities). Final `**Grand total**` footer scoped to all rows at or after the first mark.
2. **Per-vendor** - `Step | Skill | Input | Output`. Same shape and rules as Claude. Vendor name in the heading is mapped to a capitalized form (`codex` -> `Codex`, `cursor` -> `Cursor`, `gemini` -> `Gemini`); unknown vendors render with the raw name. Codex precedes Cursor; any additional vendors follow in alphabetical order. **Caveat**: today's Codex launchers (`scripts/launch-codex-implement.sh`, `scripts/launch-codex-review.sh`) record only the `total` field and not `input`/`output`, so Codex Input/Output columns will display `0` until those scrapers are extended (out of scope for this PR; see the run-statistics PR description for the follow-up issue link).

The four-column shape is consistent across all tables. Numeric columns are right-aligned (`---:`); text columns are left-aligned (`---`). Cell text passes through a small jq sanitizer (`md_cell`) that escapes `|` (single-backslash GFM escape) and collapses CR/LF to a single space, so well-formedness of the table is preserved even if a step / skill / vendor label contains those characters.

Cache-read and cache-creation totals plus the combined "Claude total" are intentionally **not** rendered in the user-facing markdown; they mix billing rates that distort spend interpretation. Operators who want a single billable proxy can compute `input + cache_read*0.1 + cache_create*1.25 + output` from `token-ledger.sh dump` and the transcripts. Terse mode (`--since-last-mark --terse`) is unchanged in this PR and still prints the cache breakdown.

## Test Harness

`scripts/test-token-report.sh` owns fixture ledger + transcript cases, missing-source graceful output, sentinel replacement idempotency, hydrated prior-report replacement, and an oversized-report smoke case.
