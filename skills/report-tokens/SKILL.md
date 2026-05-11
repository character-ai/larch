---
name: report-tokens
description: "Use when analyzing token costs across closed GitHub issues in the current larch repo: parses token-report data, estimates Claude/Codex/Cursor cost, plots SIMPLE/HARD trends, and prints cost-reduction suggestions."
allowed-tools: Bash, Read
---

# Report Tokens

Analyze token-report data across closed GitHub issues in the current larch repository. The script finds issues whose comments contain the token-report sentinel, parses the latest structured report on each issue, estimates costs, generates SIMPLE and HARD cost-over-time plots, prints the analysis, and posts a GitHub `[Analysis Report]` issue.

## Flags

Pass any of these after the skill name (e.g. `/report-tokens --no-issue`):

- `--no-issue` — skip posting the `[Analysis Report]` GitHub issue.
- `--no-plot` — skip plot generation; text analysis is still printed.
- `--plot-from <N>` — re-plot from a prior `[Analysis Report]` issue number (skips the GitHub scan).
- `--run-id <ID>` — optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

## Step 1 - Run analysis

Parse any `--no-issue`, `--no-plot`, `--plot-from <N>`, or `--run-id <ID>` flags. The `--run-id` flag is consumed by the orchestrator and NOT forwarded to `run-analysis.sh`. Then:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/run-analysis.sh" [FLAGS]
```

where `[FLAGS]` are only the flags supported by the script (`--no-issue`, `--no-plot`, `--plot-from <N>`); `--run-id` is never included.

Script contract: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/run-analysis.md`. Rate harness: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/test-rate-assertions.sh` (contract: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/test-rate-assertions.md`).

Verify the script exited successfully. On a normal run, stdout includes `## Report Tokens Analysis` plus `Cache JSON:`. On a `--plot-from` run, stdout includes `Plots written to:` or `No plots generated.`. If it exits non-zero, stop and surface the error; do not invent partial cost results.

## NEVER

1. **NEVER treat dollar output as billing truth.** The script uses transparent default rates and prints them with the analysis because vendor pricing and model routing can drift outside larch's control.
