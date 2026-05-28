---
name: report-tokens
description: "Use when analyzing token costs from committed larch run logs for the selected skill (`--skill=design|implement`): parses per-run token reports, estimates Claude/Codex/Cursor cost, plots SIMPLE/HARD trends, and prints cost-reduction suggestions."
allowed-tools: Bash, Read
---

# Report Tokens

Analyze token costs from committed larch run logs for the selected skill (`--skill=design|implement`) in the current git repository. The script scans `larch-logs/<skill>/*/` directories, parses `token-report.json` or `token-report-final.json` (design) per run, reads workflow path from `timing-report.json` / `timing-report-final.json` or `run-params.json` (`design_classification` fallback), estimates per-run dollar costs (see **Reported vs estimated** in `run-analysis.sh` output: legacy in-Python totals vs `scripts/token-cost.sh` driven by `BUCKETS_*` when present), generates SIMPLE and HARD cost-over-time plots, prints the analysis, and optionally posts a GitHub `[Implement Analysis Report]` or `[Design Analysis Report]` issue. Tracking-issue bodies fetched via `--plot-from` may still contain the legacy markdown token-report rendering; the parser handles that shape too.

## Flags

Pass any of these after the skill name (e.g. `/report-tokens --skill implement --no-issue`):

- `--skill <name>` (**required**): `design` or `implement`. Enum-validate before invoking `run-analysis.sh`; pass through to the script.
- `--no-issue` — skip posting the analysis report GitHub issue.
- `--no-plot` — skip plot generation; text analysis is still printed.
- `--plot-from <N>` — re-plot from a prior analysis-report issue number (skips the GitHub scan). Title prefix must match `--skill` before body parsing.
- `--run-id <ID>` — optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

<!-- step:1 — Run analysis -->

Parse and validate `--skill` first. Reject missing or out-of-enum values before calling the script. Parse any `--no-issue`, `--no-plot`, `--plot-from <N>`, or `--run-id <ID>` flags. The `--run-id` flag is consumed by the orchestrator and NOT forwarded to `run-analysis.sh`. Then:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/run-analysis.sh" --skill "<name>" [FLAGS]
```

where `[FLAGS]` are only the flags supported by the script (`--no-issue`, `--no-plot`, `--plot-from <N>`); `--run-id` is never included.

Script contract: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/run-analysis.md`. Rate harness: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/test-rate-assertions.sh` (contract: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/test-rate-assertions.md`).

Verify the script exited successfully. On a normal run, stdout includes `## Report Tokens Analysis` plus `Cache JSON:`. On a `--plot-from` run, stdout includes `Plots written to:` or `No plots generated.`. If it exits non-zero, stop and surface the error; do not invent partial cost results.

## NEVER

1. **NEVER treat dollar output as billing truth.** The script uses transparent default rates and prints them with the analysis because vendor pricing and model routing can drift outside larch's control.
