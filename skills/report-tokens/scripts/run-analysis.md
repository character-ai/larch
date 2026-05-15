# run-analysis.sh contract

`skills/report-tokens/scripts/run-analysis.sh` is the coordinator for `/report-tokens`.

## Purpose

Scan committed larch run logs under `larch-logs/implement/*/` in the current git repository root, parse the token report for each run (reading `manifest.json` for metadata, `token-report.json` for token data with `token-report.md` fallback, and `timing-report.json` or the plan-review tally for workflow-path inference), estimate per-run dollar costs for Claude/Codex/Cursor/Gemini, generate SIMPLE and HARD cost-over-time PNG plots, print a written analysis, and optionally post a GitHub `[Analysis Report]` issue with the results and raw per-run data.

## Primary caller

- `skills/report-tokens/SKILL.md` Step 1.

## Inputs

The script accepts optional flags:

- `--no-issue`: skip posting the `[Analysis Report]` GitHub issue after analysis.
- `--no-plot`: skip plot generation; textual analysis is still printed.
- `--plot-from <N>`: re-plot from a prior `[Analysis Report]` issue (skips the GitHub scan and analysis; fetches the issue body, extracts the raw per-issue JSON block, and generates plots). **Plot-only**: this mode regenerates SIMPLE/HARD cost-over-time PNGs only; it does not rebuild the markdown analysis text or per-day cost trend tables.

Optional environment variables:

- `LARCH_REPORT_TOKENS_REPO=<owner/repo>` overrides repository resolution.
- `LARCH_REPORT_TOKENS_LIMIT=<N>` limits the number of matching issues fetched after search.
- `LARCH_REPORT_TOKENS_NO_OPEN=1` suppresses opening generated PNGs.
- `LARCH_RATE_<VENDOR>_<FIELD>` overrides the printed default rates in USD per million tokens.
- `LARCH_REPORT_TOKENS_ACTUAL_SPEND=<USD>` when set, prints a reconciliation line at the end of the report (`tracked=$X  actual=$Y  delta=Z%`). Contains billing data — use `--no-issue` when set to avoid posting actual spend figures to a public GitHub issue.

## File access

The scan uses:

- `git -C "$(pwd)" rev-parse --show-toplevel` to locate the repository root.
- `larch-logs/implement/*/manifest.json` — provides `issue_number`, `updated_at`, `started_at` per run.
- `larch-logs/implement/*/token-report.json` — preferred structured token data. The script falls back to `token-report.md` for older logs.
- `larch-logs/implement/*/timing-report.json` — preferred workflow path source via `.workflow_path`.
- `larch-logs/implement/*/plan-review-tally.json` — fallback workflow-path source via `.body // .tally`; starts with `"Quick mode"` or `"Both externals unavailable"` → `SIMPLE`; non-empty other value → `HARD`; absent or unrecognized → `unknown`.
- `larch-logs/implement/*/plan-review-tally.ndjson` — legacy fallback with the same `.body // .tally` rule. Falls back to reading the first raw line when the file is not valid NDJSON (handles older plain-text format).

`gh` is required for repository resolution (`gh repo view`, used for URL construction; bypass via `LARCH_REPORT_TOKENS_REPO`), for posting the `[Analysis Report]` issue (active when `--no-issue` is absent), and for `--plot-from` (fetching a prior report issue body). `jq` and `python3` are always required. Missing commands are hard failures.

## Parsing invariants

- Token data is read directly from `token-report.json` files when present and converted to the existing cost totals without markdown parsing.
- Legacy token data is read directly from `token-report.md` files, which contain `### Claude` / `**Grand total**` headings without sentinel wrappers. The `latest_token_block` function's fallback (`if "### Claude" in text or "**Grand total**" in text: return text`) handles this format.
- Claude `**Grand total**` rows support both the current six-cell table shape (`Step`, `Skill`, input, cache read, cache create, output) and the legacy four-cell shape (`Step`, `Skill`, input, output).
- Codex/Cursor/Gemini `**Grand total**` rows use the five-cell vendor table shape (`Step`, `Skill`, input, output, total).
- `workflow_path` is stored directly in the cache for structured logs. Legacy markdown runs still inject `**Workflow path**: SIMPLE|HARD|unknown` into the body text so the Python `parse_workflow_path` function finds it without changes.
- Run-level JSON is cached under a fresh `${TMPDIR:-/tmp}/larch-report-tokens.*` directory. The cache file is written via a temporary file and `mv`.

## Outputs

Stdout contains progress lines while fetching and then a markdown analysis with:

- cache JSON path
- generated plot paths, or a plot-skipped reason
- rates used
- aggregate cost by workflow
- top SIMPLE issues by estimated cost
- HARD phase breakdown
- cache-read dominance
- cost-reduction suggestions
- per-day cost trend tables, bucketed by `manifest.json` `started_at` date, for Total/Claude/Codex/Cursor cost across SIMPLE and HARD workflows

After the textual analysis, the script posts a GitHub issue titled `[Analysis Report] Token costs as of <YYYY-MM-DD HH:MM UTC>` unless `--no-issue` is passed. The issue body contains the full analysis text plus a fenced JSON block with raw per-issue data (`number`, `workflow`, `started_at`, `closed_at`, `cost`) for re-plotting via `--plot-from`.

Generated plots are written to a temporary directory as `larch-report-tokens-simple.png` and `larch-report-tokens-hard.png`. On macOS, the script attempts to open them with `open` unless `LARCH_REPORT_TOKENS_NO_OPEN=1` is set. Plotting runs in a child Python process so missing or crashing `matplotlib` skips plot generation without losing the textual analysis. Pass `--no-plot` to skip plot generation entirely.

## Cost model

The default rates are transparent estimates, not billing truth. Claude uses separate input/cache-read/cache-create/output rates; Codex, Cursor, and Gemini use input/output plus an optional aggregate rate for total-only or hidden cache-like vendor tokens. Codex (GPT-5.5) reports only an aggregate `tokens used` value on stderr, so the `aggregate=$5/M` is a working approximation of the true input-heavy mix. Override rates with environment variables whenever model routing or vendor pricing changes. Source URLs for default values are cited in the RATES dict comment block in the Python section.

## Known limitations

- **Codex long-context surcharge (D7)**: GPT-5.5 prompts >272K input tokens incur 2× input and 1.5× output pricing for the full session. larch does not track prompt length per-run, so this surcharge is silently dropped. Impact is low in practice (most Codex reviewer calls are under 272K).
- **Codex cached vs uncached input (D8)**: OpenAI charges $0.50/M for cached Codex input vs $5/M for uncached — a 10× difference. Codex CLI does not expose cache hit info on stderr today. Until it does, the analyzer uses only the aggregate rate and cannot distinguish cached vs uncached spend. When cache info is exposed, mirror the Claude `cache_read`/`cache_create` column shape in the Codex rate dict.

## Edit-in-sync

When token-report table shapes change in `scripts/token-report.sh`, update this parser and contract in the same PR.
