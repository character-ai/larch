---
name: report-tokens
description: "Use when analyzing token costs across closed GitHub issues in the current larch repo: parses token-report data, estimates Claude/Codex/Cursor cost, plots SIMPLE/HARD trends, and prints cost-reduction suggestions."
allowed-tools: Bash, Read
---

# Report Tokens

Analyze token-report data across closed GitHub issues in the current larch repository. The script finds issues whose comments contain the token-report sentinel, parses the latest structured report on each issue, estimates costs, writes a JSON cache, generates SIMPLE and HARD cost-over-time plots, opens the plots when supported, and prints the written analysis.

## Step 1 - Run analysis

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/run-analysis.sh"
```

Script contract: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/run-analysis.md`.

Verify the script exited successfully and stdout includes `## Report Tokens Analysis` plus `Cache JSON:`. If it exits non-zero, stop and surface the error; do not invent partial cost results.

## NEVER

1. **NEVER treat dollar output as billing truth.** The script uses transparent default rates and prints them with the analysis because vendor pricing and model routing can drift outside larch's control.
