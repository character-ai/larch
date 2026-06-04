---
name: report-tokens
description: "Use when analyzing token costs from committed larch run logs for `--skill=design|implement`: price token reports, optionally plot trends, and print cost-reduction suggestions."
allowed-tools: Bash, Read
---

# Report Tokens

Analyze token costs from committed larch run logs for the selected skill (`--skill=design|implement`) in the current git repository. The wrapper delegates to `${CLAUDE_PLUGIN_ROOT}/python/report_tokens_cli.py`, which scans `larch-logs/<skill>/*/`, reads the skill-specific token report JSON files, prices each run through `scripts/token-cost.sh`, prints a markdown analysis, writes a durable NDJSON cache snapshot, optionally generates plots, and optionally posts a GitHub `[Implement Analysis Report]` or `[Design Analysis Report]` issue.

For `--skill=implement`, graph and per-day trend output aggregates all runs into one `All runs` series/table set, including `unknown` workflows. For `--skill=design`, SIMPLE/HARD split output is retained. The filed issue intentionally omits raw per-issue JSON and actual-spend reconciliation unless `LARCH_REPORT_TOKENS_POST_ACTUAL_SPEND=1` is set.

## Flags

Pass any of these after the skill name (for example, `/report-tokens --skill implement --no-issue`):

- `--skill <name>` (**required**): `design` or `implement`. Enum-validate before invoking `run-analysis.sh`; pass through to the script.
- `--no-issue` — skip posting the analysis report GitHub issue. `LARCH_REPORT_TOKENS_NO_ISSUE=1` has the same effect.
- `--no-plot` — skip plot generation; text analysis is still printed. `LARCH_REPORT_TOKENS_NO_PLOT=1` has the same effect.
- `--run-id <ID>` — optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

<!-- step:1 — Run analysis -->

Parse and validate `--skill` first. Reject missing or out-of-enum values before calling the script. Parse any `--no-issue`, `--no-plot`, or `--run-id <ID>` flags. The `--run-id` flag is consumed by the orchestrator and NOT forwarded to `run-analysis.sh`. Then:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/run-analysis.sh" --skill "<name>" [FLAGS]
```

where `[FLAGS]` are only `--no-issue` and/or `--no-plot`; `--run-id` is never included.

Script contract: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/run-analysis.md`. Plot subprocess contract: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/plot-cost-over-time.md`; helper: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/plot-cost-over-time.py`. Quiet wrapper harness: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/test-run-analysis-quiet.sh` with sibling `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/test-run-analysis-quiet.md`.

Verify the script exited successfully. On a normal run, stdout includes `## Report Tokens Analysis` plus `Cache JSON: <path>`. If it exits non-zero, stop and surface the error; do not invent partial cost results. The wrapper restores caller-visible stdout/stderr after `lib-quiet` initialization, so scan warnings and issue-creation failures are visible to callers.

## NEVER

1. **NEVER treat dollar output as billing truth.** The script uses transparent default rates and prints them with the analysis because vendor pricing and model routing can drift outside larch's control.
2. **NEVER forward removed replot flags.** Re-run against committed `larch-logs` instead.
