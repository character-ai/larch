---
name: report-tokens
description: "Use when analyzing token costs from committed larch run logs for `--skill=design|implement`: price token reports, optionally plot trends, and print cost-reduction suggestions."
allowed-tools: Bash, Read
---

# Report Tokens

Analyze token costs from committed larch run logs for the selected skill (`--skill=design|implement`) in the current git repository. The CLI delegates to `${CLAUDE_PLUGIN_ROOT}/python/larch/report/report_tokens_cli.py`, which scans `larch-logs/<skill>/*/`, reads the skill-specific token report JSON files, prices each run through `python/larch/report/report_tokens_cost.py`, prints a markdown analysis, writes a durable NDJSON cache snapshot, optionally generates plots, and optionally posts a GitHub `[Implement Analysis Report]` or `[Design Analysis Report]` issue.

For `--skill=implement`, reports carry no workflow dimension and graph/per-day trend output aggregates all runs into one `All runs` series/table set. For `--skill=design`, one aggregate report is generated. The filed issue intentionally omits raw per-issue JSON and actual-spend reconciliation unless `LARCH_REPORT_TOKENS_POST_ACTUAL_SPEND=1` is set.

Rate overrides: set environment variables documented in `docs/configuration-and-permissions.md` before invoking. See `docs/python-migration.md` for the migration playbook.

## Flags

Pass any of these after the skill name (for example, `/report-tokens --skill implement --no-issue`):

- `--skill <name>` (**required**): `design` or `implement`. Enum-validate before invoking the CLI; pass through to the module.
- `--no-issue` — skip posting the analysis report GitHub issue. `LARCH_REPORT_TOKENS_NO_ISSUE=1` has the same effect.
- `--no-plot` — skip plot generation; text analysis is still printed. `LARCH_REPORT_TOKENS_NO_PLOT=1` has the same effect.
- `--run-id <ID>` — optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).

<!-- step:1 — Run analysis -->

Parse and validate `--skill` first. Reject missing or out-of-enum values before calling the CLI. Parse any `--no-issue`, `--no-plot`, or `--run-id <ID>` flags. The `--run-id` flag is consumed by the orchestrator and NOT forwarded to the CLI. Then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" report-tokens analyze --skill "<name>" [FLAGS]
```

where `[FLAGS]` are only `--no-issue` and/or `--no-plot`; `--run-id` is never included.

Plot subprocess contract: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/plot-cost-over-time.md`; helper: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/plot-cost-over-time.py`.

Verify the CLI exited successfully. On a normal run, stdout includes `## Report Tokens Analysis` plus `Cache JSON: <path>`. If it exits non-zero, stop and surface the error; do not invent partial cost results. The CLI uses Python quiet routing via `quiet_init`, so scan warnings and issue-creation failures are visible to callers.

## NEVER

1. **NEVER treat dollar output as billing truth.** The CLI uses transparent default rates and prints them with the analysis because vendor pricing and model routing can drift outside larch's control.
2. **NEVER forward removed replot flags.** Re-run against committed `larch-logs` instead.
