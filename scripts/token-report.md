# token-report.sh

**Purpose**: Render `/implement` token-spend reports by combining Claude transcript usage with the session token ledger. The script is observability-only and is never load-bearing.

## Relationship to scripts/token-tally.md

`scripts/token-tally.sh` remains the `/research` lane-token helper. It writes explicit sidecars and can optionally render a cost column. `scripts/token-report.sh` is a separate `/implement` PoC that reads Claude transcript usage and the `token-ledger.sh` JSONL ledger. Dollar summaries (`--summary`, markdown cost surfaces) delegate to `scripts/token-cost.sh` via the same per-bucket counts as JSON `BUCKETS_*` when available.

## Claude usage deduplication

Claude API responses may appear on multiple JSONL rows with identical `requestId`, `message.id`, and usage fields. Before aggregation, usage rows are grouped by `(requestId, message.id)` (empty keys normalized) and **one representative row per group** is kept (`map(.[0])` — not summed). When both ids are empty, the group key includes a usage fingerprint so distinct bootstrap rows with different token counts do not collapse together.

## Subcommands

- `--since-last-mark --terse` prints one line for the most recent ledger mark:
  `Step N — <name>: claude=<total> tokens (input=A cache_read=B cache_create=C output=D); vendor=<sum> (codex=X, cursor=Y)`.
- `--summary` prints one dollar-primary grand-total line (same format as `render-cost-line.sh`):  
  `💰 Cost: TOTAL ~$X.XX — Claude $A.AA, Codex $B.BB, Cursor $C.CC  |  Tokens: <T>k`  
  Used as the default brief output in `/implement` Step 17 when `LARCH_VERBOSE_TOKENS` is unset. **Print this line verbatim in chat — do not paraphrase.**
- `--full --markdown [--output FILE]` renders a markdown table grouped by step with indented skill rows and vendor rows.
- `--full --format json [--output FILE]` renders a JSON object with `vendors`, `claude.per_step`, `claude.totals`, one sibling object per non-Claude vendor, and `BUCKETS_claude` / `BUCKETS_codex` / `BUCKETS_cursor` (per-bucket totals aligned with `token-cost.sh` flags).
- `--buckets --vendor claude|codex|cursor` (with `--ledger` / `--transcript` / session hooks as for other modes) prints one line of `KEY=value` bucket counts for stdout (test/CI helper).
- `--append-token-report FILE` renders the full table and idempotently replaces or appends a sentinel-bracketed block in `FILE`. Legacy callers may still use this mode; production `/implement` now appends structured records through `scripts/larch-log.sh`:

```
<!-- token-report-begin -->
## Token Report

...
<!-- token-report-end -->
```

When the target file is damaged so that exactly one of the two markers is present (a half-written prior run, manual edit, or partial write), `replace_token_block` normalizes the file: with a lone begin marker, content from the marker through end-of-file is dropped before appending a fresh block; with a lone end marker, content from the head through the marker is dropped. A stderr warning describing the lone-marker case is printed so the corruption stays observable. This prevents accumulating duplicate `## Token Report` blocks against a broken-prefix report file.

`replace_token_block` uses whole-line anchored regexes (`^[[:space:]]*<!-- token-report-begin -->[[:space:]]*$` and the matching `-end-` variant) for BOTH the presence probes (`grep -Eq`) at the top of the function AND the awk rewrite below, consistent between probe and rewrite paths. A prose / table-cell line that merely *mentions* the marker substring is not treated as a structural sentinel; `token-report.sh` always emits the markers on their own line, so the whole-line constraint is the author-side contract. Probe / rewrite parity is load-bearing: aligning both with the same regex prevents a data-loss path where substring presence detection would route into the matched-pair or lone-marker branches but the awk rewrite would never fire on a structural line. Files whose marker mentions appear only in prose route through the no-marker append path: existing content is preserved verbatim and a fresh block is appended at EOF.

`--ledger`, `--transcript`, and `--session-dir` are test hooks. Production calls resolve the ledger through `token-ledger.sh dump` and the transcript through `token-claude-source.sh`.

## Cross-cutting Failure Mode

Token reporting must never block `/implement`.

- `token-report.sh`: prints `Token report unavailable: <reason>` to stderr and exits 0. With `LARCH_DEBUG_TOKEN_REPORT` enabled (see "LARCH_DEBUG_TOKEN_REPORT opt-in jq diagnostics" below) and a non-empty captured jq stderr, the message gains a fixed trailing parenthetical `(jq stderr captured; debug)` (preceded by a single space) — never the absolute path. The actual jq stderr file path is emitted to the script's own stderr as `token-report.sh: jq stderr captured at <path>`. Consumers matching the `Token report unavailable:` prefix continue to work; consumers expecting an exact-line match must accept the optional fixed-phrase suffix.
- `token-ledger.sh`: warns on stderr and exits 0.
- `token-claude-source.sh`: prints `STATUS=unavailable` / `REASON=<msg>` to stdout and exits 1.
- Launcher scrape blocks: silent on failure; diagnostics stay in sidecars or stderr and never pollute launcher stdout.

### `LARCH_DEBUG_TOKEN_REPORT` opt-in jq diagnostics

By default the embedded `jq` invocation in `render_jq` redirects stderr to `/dev/null` so a malformed ledger or transcript only surfaces the generic `Token report unavailable: failed to parse token sources` message. Set `LARCH_DEBUG_TOKEN_REPORT` to one of the explicit truthy values (`1`, `true`, `TRUE`, `True`, `yes`, `YES`, `Yes`, `on`, `ON`, `On`) to redirect jq stderr to a freshly-allocated `mktemp` file under `${TMPDIR:-/tmp}` named `larch-token-report-jq-stderr-XXXXXX` (chmod 0600 explicitly applied as defense in depth). On render failure with non-empty stderr, the unavailable message gets a fixed `... (jq stderr captured; debug)` suffix on stdout, and the actual file path is emitted to the script's own stderr (`token-report.sh: jq stderr captured at <path>`) so the operator can read the actual jq diagnostics there. The published surface (stdout, which can flow into larch-log batches, tracking-issue summaries, and PR bodies) never carries the TMPDIR/username-bearing absolute path. On render success — or render failure with empty stderr — the temp file is removed so successful runs do not litter `$TMPDIR`. The redirect is a plain stderr redirect, not a `tee` — jq diagnostics go only to the temp file, not also to the controlling terminal.

Any other value (including `no`, `off`, `disabled`, `0`, empty, or unset) preserves the default silent behavior — the env var is parsed against an explicit allowlist of truthy spellings, not as "anything non-empty / non-zero," so common negatives stay safely off. `mktemp` failure (e.g. an out-of-space `$TMPDIR`) degrades silently to `/dev/null`, so the debug knob never breaks the production render path. The env var is purely a development knob, not a production observability surface.

## Skill Attribution

The Skill column in the Claude table has two categories:

- **Native attribution** (`attributionSkill` present in the JSONL): Claude Code's runtime sets this field whenever a Skill tool is active. The value is the exact skill name (e.g. `larch:implement`, `larch:design`).
- **Inferred attribution** (`inferred:<step>`): when `attributionSkill` is null and the row's timestamp falls within a step-mark window `[mark.ts, next_mark.ts)`, the report infers the step name from the enclosing window. The label is deliberately neutral — it means "null attribution inside this step window" and does NOT claim the tokens are from orchestrator overhead vs. user-driven interruptions; both can appear as null-attribution turns inside a step window.
- **Unattributed**: rows with null `attributionSkill` that fall before the first ledger mark. In practice, `claude_table` renders only rows at or after the first mark, so "unattributed" rows do not appear in the rendered table — they are excluded from step rows and the grand total.

The inferred label assignment uses the same half-open interval `[mark.ts, next_mark.ts)` as the step-slice helpers. The inference applies to all transcripts slurped (main session file and subagent files in `session_dir/subagents/`); subagent null-attribution rows receive the same inferred label as parent-session rows, which is acceptable because the label makes no causal claim.

## Table Shape

The full markdown output renders as **one Claude table plus one table per vendor present in the run**, each preceded by an `### <vendor>` heading and a blank line. The Claude table is always emitted; vendor tables are emitted only when at least one row of that vendor exists at or after the first ledger mark.

1. **Claude** - `Step | Skill | Claude Input | Claude Cache Read | Claude Cache Create | Claude Output`. One step-summary row per ledger mark followed by per-skill detail rows (blank Step cell + skill identifier in the Skill column; no indentation marker, no HTML entities). Final `**Grand total**` footer scoped to all rows at or after the first mark. Cache reads (typically 5-20x uncached input on long orchestrators, billed at the cached-input rate) and cache creates (billed at a write premium) are surfaced as their own columns so reports do not understate Anthropic input volume. The Skill column contains native skill names, `inferred:<step>` labels for null-attribution rows within a step window, or nothing when no rows exist for a step — see "Skill Attribution" above.

The Claude table uses `Step | Skill | Claude Input | Claude Cache Read | Claude Cache Create | Claude Output`; per-vendor tables use `Step | Skill | Input | Output | Total`. Numeric columns are right-aligned (`---:`); text columns are left-aligned (`---`). Cell text passes through a small jq sanitizer (`md_cell`) that escapes `|` (single-backslash GFM escape) and collapses CR/LF to a single space, so well-formedness of the table is preserved even if a step / skill / vendor label contains those characters. Programmatic consumers must key off the `### <name>` heading or header row to choose column cardinality.

The four numeric Claude columns are kept separate (rather than collapsed into a combined "Claude total") because each carries a different billing rate; mixing them obscures spend interpretation. Operators who want a single billable proxy can compute `input + cache_read*0.1 + cache_create*1.25 + output` from these columns directly — these illustrative coefficients reflect the cached-input discount and cache-write premium relative to base input at the time this doc was written; verify against current Anthropic pricing before relying on the resulting figure for spend decisions. Terse mode (`--since-last-mark --terse`) prints the same `cache_read=A cache_create=B` breakdown.

## Test Harness

`scripts/test-token-report.sh` owns fixture ledger + transcript cases, markdown and JSON full-report output, missing-source graceful output, sentinel replacement idempotency, hydrated prior-report replacement, and an oversized-report smoke case. `scripts/test-token-report-dedup.sh` pins dedup invariants.
