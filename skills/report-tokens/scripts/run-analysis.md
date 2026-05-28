# run-analysis.sh contract

`skills/report-tokens/scripts/run-analysis.sh` is the coordinator for `/report-tokens`.

## Purpose

Scan committed `larch-logs/<skill>/*/` run directories for the required `--skill` (`design` or `implement`), estimate per-run spend, and print markdown tables. Design reads `token-report-final.json` / `timing-report-final.json`; implement reads `token-report.json` / `timing-report.json`. Totals used for plots and headline aggregates prefer **`scripts/token-cost.sh`** when `CLAUDE_PLUGIN_ROOT` is set: JSON reports with `BUCKETS_*` invoke per-bucket pricing; otherwise blended aggregate counts are used. A **### Reported vs estimated (per issue)** table compares the frozen legacy in-Python estimator (pre-DE-2622 defaults) with the `token-cost.sh` estimate for the same run so operators can see drift after pricing/dedup fixes. Raw GitHub issue data (when `--no-issue` is off) now includes `cost_reported` and `cost_estimated` alongside `cost` for downstream tooling.

## Primary caller

- `skills/report-tokens/SKILL.md` Step 1.

## Inputs

The script accepts:

- `--skill <name>` (**required**): `design` or `implement`. Selects log root and artifact filenames.
- `--no-issue`: skip posting the analysis-report GitHub issue after analysis.
- `--no-plot`: skip plot generation; textual analysis is still printed.
- `--plot-from <N>`: re-plot from a prior analysis-report issue (skips the scan). Fetches `title` and `body`; validates title prefix for `--skill` before parsing body. **Plot-only**: regenerates SIMPLE/HARD PNGs only.

New issues use `[Implement Analysis Report]` or `[Design Analysis Report]` titles (not unprefixed `[Analysis Report]`). `--skill=implement` `--plot-from` accepts legacy `[Analysis Report]` or `[Implement Analysis Report]` titles.

Optional environment variables:

- `LARCH_REPORT_TOKENS_REPO=<owner/repo>` overrides repository resolution.
- `LARCH_REPORT_TOKENS_LIMIT=<N>` limits the number of matching issues fetched after search.
- `LARCH_REPORT_TOKENS_NO_OPEN=1` suppresses opening generated PNGs.
- `LARCH_RATE_<VENDOR>_<FIELD>` overrides the printed default rates in USD per million tokens.
- `LARCH_REPORT_TOKENS_ACTUAL_SPEND=<USD>` when set, prints a reconciliation line at the end of the report (`tracked=$X  actual=$Y  delta=Z%`). Contains billing data — use `--no-issue` when set to avoid posting actual spend figures to a public GitHub issue.

## File access

The scan uses:

- `git -C "$(pwd)" rev-parse --show-toplevel` to locate the repository root.
- `larch-logs/<skill>/*/manifest.json` — provides `issue_number`, `updated_at`, `started_at` per run.
- `larch-logs/<skill>/*/token-report.json` or `token-report-final.json` (design) — structured token data; runs without the expected file are skipped.
- `larch-logs/<skill>/*/timing-report.json` or `timing-report-final.json` (design) — preferred workflow path source via `scripts/read-workflow-path.sh`.
- `larch-logs/<skill>/*/run-params.json` — fallback workflow path source; `design_classification` accepted when exactly `SIMPLE` or `HARD`.

`gh` is required for repository resolution (`gh repo view`, used for URL construction; bypass via `LARCH_REPORT_TOKENS_REPO`), for posting the skill-prefixed analysis-report issue (`[Implement Analysis Report]` or `[Design Analysis Report]`, active when `--no-issue` is absent), and for `--plot-from` (fetching a prior report issue body). `jq` and `python3` are always required. Missing commands are hard failures.

## Parsing invariants

- Token data is read directly from `token-report.json` files and converted to the existing cost totals without markdown parsing.
- `--plot-from <N>` paths still parse legacy markdown out of tracking-issue bodies fetched from GitHub: the `latest_token_block` fallback (`if "### Claude" in text or "**Grand total**" in text: return text`) handles those, and `parse_report` accepts both the current six-cell Claude `**Grand total**` table shape (`Step`, `Skill`, input, cache read, cache create, output) and the legacy four-cell shape (`Step`, `Skill`, input, output).
- `workflow_path` is stored directly in the cache for structured logs; when absent, `design_classification` is accepted as the tier label fallback.
- Run-level JSON is cached under a fresh `${TMPDIR:-/tmp}/larch-report-tokens.*` directory. The cache file is written via a temporary file and `mv`.

## Outputs

Stdout contains progress lines while fetching and then a markdown analysis with:

- cache JSON path
- generated plot paths, or a plot-skipped reason
- rates used
- aggregate cost by workflow (count, total, median, mean, max per SIMPLE/HARD/unknown)
- top SIMPLE issues by estimated cost
- HARD phase breakdown
- cache-read dominance
- cost-reduction suggestions
- per-day cost trend tables, bucketed by `manifest.json` `started_at` date, for Total/Claude/Codex/Cursor cost across SIMPLE and HARD workflows

After the textual analysis, the script posts a GitHub issue titled `[Implement Analysis Report] Token costs as of <YYYY-MM-DD HH:MM UTC>` or `[Design Analysis Report] Token costs as of <YYYY-MM-DD HH:MM UTC>` unless `--no-issue` is passed. The issue body contains the full analysis text plus a fenced JSON block with raw per-issue data (`number`, `workflow`, `started_at`, `closed_at`, `cost`, `cost_reported`, `cost_estimated`) for re-plotting via `--plot-from`. Before the temporary markdown file is written, the body is passed through `scripts/redact-secrets.sh` and `scripts/redact-tmpdir-paths.sh`, plus a report-specific tmpdir scrub for `larch-report-tokens.*` paths, then passed to `gh issue create --body-file` per `.claude/rules/gh-body-file.md`; do not pass the analysis text through inline `--body`.

Generated plots are written to a temporary directory as `larch-report-tokens-simple.png` and `larch-report-tokens-hard.png`. On macOS, the script attempts to open them with `open` unless `LARCH_REPORT_TOKENS_NO_OPEN=1` is set. Plotting runs in a child Python process so missing or crashing `matplotlib` skips plot generation without losing the textual analysis. Pass `--no-plot` to skip plot generation entirely.

## Cost model

## Known limitations

- **Codex long-context surcharge (D7)**: GPT-5.5 prompts >272K input tokens incur 2× input and 1.5× output pricing for the full session. larch does not track prompt length per-run, so this surcharge is silently dropped. Impact is low in practice (most Codex reviewer calls are under 272K).
- **Codex cached vs uncached input (D8)**: OpenAI charges $0.50/M for cached Codex input vs $5/M for uncached — a 10× difference. Codex CLI does not expose cache hit info on stderr today. Until it does, the analyzer uses only the aggregate rate and cannot distinguish cached vs uncached spend. When cache info is exposed, mirror the Claude `cache_read`/`cache_create` column shape in the Codex rate dict.

## Edit-in-sync

When token-report table shapes change in `scripts/token-report.sh`, update this parser and contract in the same PR.
