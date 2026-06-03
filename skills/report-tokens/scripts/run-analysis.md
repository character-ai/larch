# run-analysis.sh contract

`skills/report-tokens/scripts/run-analysis.sh` is the thin shell wrapper for the Python `/report-tokens` analyzer.

## Purpose

Validate the required `--skill` value, initialize `lib-quiet`, restore caller-visible stdout/stderr, and `exec python3 ${CLAUDE_PLUGIN_ROOT}/python/report_tokens_cli.py`. The Python modules scan committed `larch-logs/<skill>/*/` run directories, price every parseable run through `scripts/token-cost.sh`, render markdown, optionally call the subprocess-isolated matplotlib helper, and optionally file a skill-prefixed GitHub issue.

## Primary caller

- `skills/report-tokens/SKILL.md` Step 1.

## Inputs

The wrapper accepts:

- `--skill <name>` (**required**): `design` or `implement`.
- `--no-issue`: skip posting the analysis-report GitHub issue after analysis.
- `--no-plot`: skip plot generation; textual analysis is still printed.

The prior replot-from-issue mode has been removed. The analyzer scans committed run-log JSON directly and does not parse previous report issue bodies.

Optional environment variables:

- `LARCH_REPORT_TOKENS_REPO=<owner/repo>` overrides repository resolution.
- `LARCH_REPORT_TOKENS_LIMIT=<N>` limits the number of run directories scanned.
- `LARCH_REPORT_TOKENS_NO_ISSUE=1` and `LARCH_REPORT_TOKENS_NO_PLOT=1` mirror the CLI flags.
- `LARCH_REPORT_TOKENS_NO_OPEN=1` suppresses opening generated PNGs on macOS.
- `LARCH_REPORT_TOKENS_ACTUAL_SPEND=<USD>` prints a stdout-only reconciliation line.
- `LARCH_REPORT_TOKENS_POST_ACTUAL_SPEND=1` allows that reconciliation section into the posted issue.
- `LARCH_RATE_*` aliases and legacy `LARCH_*_RATE_PER_M` variables override display/fallback rates; effective values are forwarded to `scripts/token-cost.sh`.

## File access

The scan uses:

- `larch-logs/design/*/token-report-final.json` and `timing-report-final.json`.
- `larch-logs/implement/*/token-report.json` and `timing-report.json`.
- `manifest.json` for issue number and timestamps.
- `run-params.json` as a fallback workflow source.

Invalid or incomplete per-run JSON emits a stderr warning and skips that run; it does not abort the whole scan. Valid token-report JSON without numeric vendor totals or `BUCKETS_*` data is skipped instead of being treated as zero cost.

## Outputs

Stdout contains markdown beginning with `## Report Tokens Analysis` and ending with `Cache JSON: <path>`, where the path points at a durable NDJSON snapshot under a `larch-report-tokens.*` temporary directory. The report includes aggregate workflow costs, vendor totals, top runs, per-day trend tables, display/fallback rates, and cost-reduction suggestions.

For `--skill=implement`, plots and per-day tables use one aggregate `All runs` view. For `--skill=design`, SIMPLE/HARD split views are retained. The rendered report does not include a reported-vs-estimated comparison table or raw per-issue JSON block.

Generated plots are written by `plot-cost-over-time.py`, the only matplotlib-importing file. `python/report_tokens_plot.py` passes a JSON payload that follows `plot-cost-over-time.md`, sets `MPLCONFIGDIR` under the persistent plot directory, and treats child failures as visible plot skips.

Posted issues are trimmed on the final redacted UTF-8 bytes before `gh issue create`. Low-priority sections are removed first and a top-of-issue truncation notice names omitted sections. If the body still exceeds GitHub's limit, or if `gh issue create` returns non-zero, the wrapper surfaces the error on real stderr and exits non-zero. The issue body is passed through a file-backed `gh issue create --body-file` path.

## Cost model

`scripts/token-cost.sh` is the sole pricing authority for headline/table totals. Python display-rate math is fallback-only and emits a warning when used because `token-cost.sh` is unavailable, fails, or returns incomplete KV output.

Rate compatibility aliases:

| Effective field | Preferred env | Legacy/env alias |
| --- | --- | --- |
| Claude input | `LARCH_CLAUDE_INPUT_RATE_PER_M` | `LARCH_RATE_CLAUDE_INPUT` |
| Claude cache read | `LARCH_CLAUDE_CACHE_READ_RATE_PER_M` | `LARCH_RATE_CLAUDE_CACHE_READ` |
| Claude cache create 5m | `LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M` | `LARCH_RATE_CLAUDE_CACHE_CREATE`, `LARCH_RATE_CLAUDE_CACHE_CREATE_5M` |
| Claude cache create 1h | `LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M` | `LARCH_RATE_CLAUDE_CACHE_CREATE_1H` |
| Claude output | `LARCH_CLAUDE_OUTPUT_RATE_PER_M` | `LARCH_RATE_CLAUDE_OUTPUT` |
| Codex input | `LARCH_CODEX_INPUT_RATE_PER_M` | `LARCH_RATE_CODEX_INPUT` |
| Codex cached input | `LARCH_CODEX_CACHED_INPUT_RATE_PER_M` | `LARCH_RATE_CODEX_CACHE_READ`, `LARCH_RATE_CODEX_CACHED_INPUT` |
| Codex output | `LARCH_CODEX_OUTPUT_RATE_PER_M` | `LARCH_RATE_CODEX_OUTPUT` |
| Cursor input | `LARCH_CURSOR_INPUT_RATE_PER_M` | `LARCH_RATE_CURSOR_INPUT` |
| Cursor cache read | `LARCH_CURSOR_CACHE_READ_RATE_PER_M` | `LARCH_RATE_CURSOR_CACHE_READ` |
| Cursor output | `LARCH_CURSOR_OUTPUT_RATE_PER_M` | `LARCH_RATE_CURSOR_OUTPUT` |

## Edit-in-sync

When token-report JSON shapes change in `scripts/token-report.sh`, update `python/report_tokens_scan.py`, `python/report_tokens_cost.py`, the plot schema if needed, and the colocated Python tests in the same PR. Grep docs and skills for stale report-token flag names and removed section names after behavior changes.
