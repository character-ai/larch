---
name: difficulty-calibration
description: "Use when comparing predicted and realized larch difficulty tiers from committed run logs. Diagnostic only; changes no thresholds, panels, points, or routing."
argument-hint: "[--log-root DIR] [--out FILE]"
allowed-tools: Bash, Read
---

# difficulty-calibration

Use `$ARGUMENTS` as optional CLI flags for the analyzer.

## Verification

After running the backing script, validate that the output includes a difficulty
classification and any required evidence before reporting the result.

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Analyze predicted versus realized difficulty tiers from committed `larch-logs/` data.

The analyzer is read-only unless `--out FILE` is provided. It reads committed logs only. It does **not** change thresholds, panels, reviewer points, token allocation, or live routing.

## Usage

`/difficulty-calibration [--log-root DIR] [--out FILE]`

## Run the Analysis

Call the analyzer via the Bash tool, forwarding any flags, then relay its markdown stdout to the user:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" difficulty-calibration analyze [flags]
```

Do not re-tally or reformat the analysis in the main agent. The CLI owns extraction, joins, realized-tier math, and rendering.

Flags:

- `--log-root DIR` - `larch-logs` directory. Default: `<git toplevel>/larch-logs`.
- `--out FILE` - write the report to `FILE` and print only `REPORT_FILE=<path>`.

## Data Model

The analyzer joins `difficulty-rating.json`, review classification TSVs, JSONL or NDJSON fallback findings, token and timing reports, and `larch-logs/rejected-analysis-verdicts.tsv` when present.

Classification source order is fixed:

- `/implement`: `round-*/findings-classification.tsv`, then run-root `review-findings-full.jsonl`.
- `/review`: `review-findings-classification-round-*.tsv`, then `review-findings.ndjson`, then run-root `review-findings-full.jsonl`.
- `/design`: `plan-review/round-*/findings-classification.tsv` only.

Realized difficulty is diagnostic and fixed: escalated runs are `HARD`; otherwise accepted in-scope finding counts map to `TRIVIAL` for 0, `MODERATE` for 1-2, and `HARD` for 3 or more. Severity does not affect the tier. Missing or malformed pre-initiative artifacts degrade to counters or `n/a` cells.
