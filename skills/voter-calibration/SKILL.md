---
name: voter-calibration
description: "Use when analyzing voter agreement, severity calibration, and chronic outliers from committed larch run logs. Diagnostic only; changes no thresholds or points."
allowed-tools: Bash, Read
---

# voter-calibration

Analyze **voter agreement**, **YES-vote severity spread**, **severity calibration score**, and chronic outlier voters from committed larch run logs.

The analyzer measures agreement and severity calibration only. It reports voter-side calibration standing. It does **not** use realized outcomes, issue fate, or reverts. It does **not** affect reviewer/proposer points, spawning, thresholds, token allocation, or live panel verdicts.

## Usage

`/voter-calibration [--log-root DIR] [--min-votes N] [--outlier-threshold R] [--high-severity-threshold R] [--era {all,pre,post}] [--era-since-date YYYY-MM-DD] [--out FILE]`

## Run the Analysis

Call the analyzer via the Bash tool, forwarding any flags, then relay its markdown stdout to the user:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/voter-calibration/scripts/voter-calibration.py" [flags]
```

Do not re-tally or re-format the analysis in the main agent. The script owns extraction, shared agreement math, and rendering.

Flags:

- `--log-root DIR` - `larch-logs` directory. Default: `<git toplevel>/larch-logs`.
- `--min-votes N` - minimum eligible votes before outlier flagging. Default: `20`.
- `--outlier-threshold R` - flag chronic outliers below this agreement rate. Default: `0.50`.
- `--high-severity-threshold R` - flag voters whose valid YES-vote severities exceed this high-severity rate. Default: `0.90`.
- `--era {all,pre,post}` - segment the corpus before and after the ground-truth incentive boundary.
- `--era-since-date YYYY-MM-DD` - override the boundary with UTC midnight on that date.
- `--out FILE` - write the report to `FILE` instead of stdout.

Direct `python3 .../voter-calibration.py` and `make test-voter-calibration` runs do not require `CLAUDE_PLUGIN_ROOT`. The script bootstraps `python/` imports from its own path; see `scripts/voter-calibration.md`.

## Acceptance Readout

- **Default post-ship:** run `--era all` after incentive #5461 ships. Auto-boundary uses `closedAt` from one scoped `gh issue view`. Compare `High Rate` and `Calibration Score` in segmented `## Pre-incentive era` and `## Post-incentive era` sections. Each section contains `## Agreement Table` and `## Voter Severity Scoreboard`.
- **Override or pre-ship:** run `--era all --era-since-date YYYY-MM-DD` when the incentive is unshipped, auto-boundary degrades, or the operator wants a manual cutoff.

## Implementation

Logic lives in `scripts/`; SKILL.md is a thin coordinator.

- `scripts/voter-calibration.py` (contract: `scripts/voter-calibration.md`) - the analyzer.
- `scripts/test-voter-calibration.sh` (contract: `scripts/test-voter-calibration.md`) - synthetic offline harness.
