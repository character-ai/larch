# token-report.sh

**Purpose**: Render `/implement` token-spend reports by combining Claude transcript usage with the session token ledger. The script is observability-only and is never load-bearing.

## Relationship to scripts/token-tally.md

`scripts/token-tally.sh` remains the `/research` lane-token helper. It writes explicit sidecars and can optionally render a cost column. `scripts/token-report.sh` is a separate `/implement` PoC that reads Claude transcript usage and the `token-ledger.sh` JSONL ledger. It reports tokens only, with no dollar conversion and no cache-discount weighting.

## Subcommands

- `--since-last-mark --terse` prints one line for the most recent ledger mark:
  `Step N — <name>: claude=<total> tokens (input=A cache_read=B cache_create=C output=D); vendor=<sum> (codex=X, cursor=Y)`.
- `--full --markdown [--output FILE]` renders a markdown table grouped by step with indented skill rows and vendor rows.
- `--append-token-report FILE` renders the full table and idempotently replaces or appends a sentinel-bracketed block in `FILE`. Production `/implement` calls write this to `$IMPLEMENT_TMPDIR/anchor-sections/token-report.md`:

```
<!-- token-report-begin -->
## Token Report

...
<!-- token-report-end -->
```

When the target file is damaged so that exactly one of the two markers is present (a half-written prior run, manual edit, or partial write), `replace_token_block` normalizes the file: with a lone begin marker, content from the marker through end-of-file is dropped before appending a fresh block; with a lone end marker, content from the head through the marker is dropped. A stderr warning describing the lone-marker case is printed so the corruption stays observable. This prevents accumulating duplicate `## Token Report` blocks against a broken-prefix anchor file.

`--ledger`, `--transcript`, and `--session-dir` are test hooks. Production calls resolve the ledger through `token-ledger.sh dump` and the transcript through `token-claude-source.sh`.

## Cross-cutting Failure Mode

Token reporting must never block `/implement`.

- `token-report.sh`: prints `Token report unavailable: <reason>` to stdout and exits 0.
- `token-ledger.sh`: warns on stderr and exits 0.
- `token-claude-source.sh`: prints `STATUS=unavailable` / `REASON=<msg>` to stdout and exits 1.
- Launcher scrape blocks: silent on failure; diagnostics stay in sidecars or stderr and never pollute launcher stdout.

### `LARCH_DEBUG_TOKEN_REPORT` opt-in jq diagnostics

By default the embedded `jq` invocation in `render_jq` redirects stderr to `/dev/null` so a malformed ledger or transcript only surfaces the generic `Token report unavailable: failed to parse token sources` message. Set `LARCH_DEBUG_TOKEN_REPORT` to a non-empty, non-zero, non-false value (`1`, `true`, `yes`, etc.) to tee jq stderr to a freshly-allocated `mktemp` file under `${TMPDIR:-/tmp}` named `larch-token-report-jq-stderr-XXXXXX`. On render failure, the path is appended to the unavailable message as `... (jq stderr at <path>)` so the operator can read the actual jq diagnostics. The file is left in place (best-effort cleanup is the operator's responsibility) — the env var is purely a development knob, not a production observability surface. `LARCH_DEBUG_TOKEN_REPORT=0`, `LARCH_DEBUG_TOKEN_REPORT=false`, and an unset value all preserve the default silent behavior. `mktemp` failure (e.g. an out-of-space `$TMPDIR`) degrades silently to `/dev/null`, so the debug knob never breaks the production render path.

## Table Shape

The full markdown output renders as **one Claude table plus one table per vendor present in the run**, each preceded by an `### <vendor>` heading and a blank line. The Claude table is always emitted; vendor tables are emitted only when at least one row of that vendor exists at or after the first ledger mark.

1. **Claude** - `Step | Skill | Claude Input | Claude Output`. One step-summary row per ledger mark followed by per-skill detail rows (blank Step cell + skill identifier in the Skill column; no indentation marker, no HTML entities). Final `**Grand total**` footer scoped to all rows at or after the first mark.
2. **Per-vendor** - `Step | Skill | Input | Output | Total`. Same shape and rules as the Claude table for the leading two columns. Vendor name in the heading is mapped to a capitalized form (`codex` -> `Codex`, `cursor` -> `Cursor`, `gemini` -> `Gemini`); unknown vendors render with the raw name. Codex precedes Cursor; any additional vendors follow in alphabetical order. **Codex CLI behavior**: the codex CLI exposes only a single aggregate token count via stderr (`tokens used`), so Codex rows render `0` in the Input and Output columns and surface the aggregate in the `Total` column. Cursor's launcher captures granular `input` / `output` / cache fields, so Cursor rows show populated Input and Output alongside `Total`; the `Total` value is the launcher-recorded ledger total, which includes cache fields not surfaced as columns, and is not necessarily `Input + Output`. For legacy vendor rows that omit the `total` ledger field entirely, the renderer falls back to `input + output + cache_read + cache_create` so the `Total` column is never visually misleading.

The Claude table uses `Step | Skill | Claude Input | Claude Output`; per-vendor tables use `Step | Skill | Input | Output | Total`. Numeric columns are right-aligned (`---:`); text columns are left-aligned (`---`). Cell text passes through a small jq sanitizer (`md_cell`) that escapes `|` (single-backslash GFM escape) and collapses CR/LF to a single space, so well-formedness of the table is preserved even if a step / skill / vendor label contains those characters. Programmatic consumers must key off the `### <name>` heading or header row to choose column cardinality.

Cache-read and cache-creation totals plus the combined "Claude total" are intentionally **not** rendered in the user-facing markdown; they mix billing rates that distort spend interpretation. Operators who want a single billable proxy can compute `input + cache_read*0.1 + cache_create*1.25 + output` from `token-ledger.sh dump` and the transcripts. Terse mode (`--since-last-mark --terse`) is unchanged in this PR and still prints the cache breakdown.

## Test Harness

`scripts/test-token-report.sh` owns fixture ledger + transcript cases, missing-source graceful output, sentinel replacement idempotency, hydrated prior-report replacement, and an oversized-report smoke case.
