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

`replace_token_block` uses whole-line anchored regexes (`^[[:space:]]*<!-- token-report-begin -->[[:space:]]*$` and the matching `-end-` variant) for BOTH the presence probes (`grep -Eq`) at the top of the function AND the awk rewrite below, parallel to `assemble-anchor.sh`'s marker-pair walks. A prose / table-cell line that merely *mentions* the marker substring is not treated as a structural sentinel; `token-report.sh` always emits the markers on their own line, so the whole-line constraint is the author-side contract. Probe / rewrite parity is load-bearing: aligning both with the same regex prevents a data-loss path where substring presence detection would route into the matched-pair or lone-marker branches but the awk rewrite would never fire on a structural line. Files whose marker mentions appear only in prose route through the no-marker append path: existing content is preserved verbatim and a fresh block is appended at EOF.

`--ledger`, `--transcript`, and `--session-dir` are test hooks. Production calls resolve the ledger through `token-ledger.sh dump` and the transcript through `token-claude-source.sh`.

## Cross-cutting Failure Mode

Token reporting must never block `/implement`.

- `token-report.sh`: prints `Token report unavailable: <reason>` to stdout and exits 0. With `LARCH_DEBUG_TOKEN_REPORT` enabled (see "LARCH_DEBUG_TOKEN_REPORT opt-in jq diagnostics" below) and a non-empty captured jq stderr, the message gains a fixed trailing parenthetical `(jq stderr captured; debug)` (preceded by a single space) — never the absolute path. The actual jq stderr file path is emitted to the script's own stderr as `token-report.sh: jq stderr captured at <path>`. Consumers matching the `Token report unavailable:` prefix continue to work; consumers expecting an exact-line match must accept the optional fixed-phrase suffix.
- `token-ledger.sh`: warns on stderr and exits 0.
- `token-claude-source.sh`: prints `STATUS=unavailable` / `REASON=<msg>` to stdout and exits 1.
- Launcher scrape blocks: silent on failure; diagnostics stay in sidecars or stderr and never pollute launcher stdout.

### `LARCH_DEBUG_TOKEN_REPORT` opt-in jq diagnostics

By default the embedded `jq` invocation in `render_jq` redirects stderr to `/dev/null` so a malformed ledger or transcript only surfaces the generic `Token report unavailable: failed to parse token sources` message. Set `LARCH_DEBUG_TOKEN_REPORT` to one of the explicit truthy values (`1`, `true`, `TRUE`, `True`, `yes`, `YES`, `Yes`, `on`, `ON`, `On`) to redirect jq stderr to a freshly-allocated `mktemp` file under `${TMPDIR:-/tmp}` named `larch-token-report-jq-stderr-XXXXXX` (chmod 0600 explicitly applied as defense in depth). On render failure with non-empty stderr, the unavailable message gets a fixed `... (jq stderr captured; debug)` suffix on stdout, and the actual file path is emitted to the script's own stderr (`token-report.sh: jq stderr captured at <path>`) so the operator can read the actual jq diagnostics there. The published surface (stdout, which flows verbatim into tracking-issue anchors and PR bodies) never carries the TMPDIR/username-bearing absolute path. On render success — or render failure with empty stderr — the temp file is removed so successful runs do not litter `$TMPDIR`. The redirect is a plain stderr redirect, not a `tee` — jq diagnostics go only to the temp file, not also to the controlling terminal.

Any other value (including `no`, `off`, `disabled`, `0`, empty, or unset) preserves the default silent behavior — the env var is parsed against an explicit allowlist of truthy spellings, not as "anything non-empty / non-zero," so common negatives stay safely off. `mktemp` failure (e.g. an out-of-space `$TMPDIR`) degrades silently to `/dev/null`, so the debug knob never breaks the production render path. The env var is purely a development knob, not a production observability surface.

## Table Shape

The full markdown output renders as **one Claude table plus one table per vendor present in the run**, each preceded by an `### <vendor>` heading and a blank line. The Claude table is always emitted; vendor tables are emitted only when at least one row of that vendor exists at or after the first ledger mark.

1. **Claude** - `Step | Skill | Claude Input | Claude Output`. One step-summary row per ledger mark followed by per-skill detail rows (blank Step cell + skill identifier in the Skill column; no indentation marker, no HTML entities). Final `**Grand total**` footer scoped to all rows at or after the first mark.
2. **Per-vendor** - `Step | Skill | Input | Output | Total`. Same shape and rules as the Claude table for the leading two columns. Vendor name in the heading is mapped to a capitalized form (`codex` -> `Codex`, `cursor` -> `Cursor`, `gemini` -> `Gemini`); unknown vendors render with the raw name. Codex precedes Cursor; any additional vendors follow in alphabetical order. **Codex CLI behavior**: the codex CLI exposes only a single aggregate token count via stderr (`tokens used`), so Codex rows render `0` in the Input and Output columns and surface the aggregate in the `Total` column. Cursor's launcher captures granular `input` / `output` / cache fields, so Cursor rows show populated Input and Output alongside `Total`; the `Total` value is the launcher-recorded ledger total, which includes cache fields not surfaced as columns, and is not necessarily `Input + Output`. For legacy vendor rows that omit the `total` ledger field entirely, the renderer falls back to `input + output + cache_read + cache_create` so the `Total` column is never visually misleading.

The Claude table uses `Step | Skill | Claude Input | Claude Output`; per-vendor tables use `Step | Skill | Input | Output | Total`. Numeric columns are right-aligned (`---:`); text columns are left-aligned (`---`). Cell text passes through a small jq sanitizer (`md_cell`) that escapes `|` (single-backslash GFM escape) and collapses CR/LF to a single space, so well-formedness of the table is preserved even if a step / skill / vendor label contains those characters. Programmatic consumers must key off the `### <name>` heading or header row to choose column cardinality.

Cache-read and cache-creation totals plus the combined "Claude total" are intentionally **not** rendered in the user-facing markdown; they mix billing rates that distort spend interpretation. Operators who want a single billable proxy can compute `input + cache_read*0.1 + cache_create*1.25 + output` from `token-ledger.sh dump` and the transcripts. Terse mode (`--since-last-mark --terse`) is unchanged in this PR and still prints the cache breakdown.

## Test Harness

`scripts/test-token-report.sh` owns fixture ledger + transcript cases, missing-source graceful output, sentinel replacement idempotency, hydrated prior-report replacement, and an oversized-report smoke case.
