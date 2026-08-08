---

# larch-run-lifecycle: shared-v1 skill=report-tokens
name: report-tokens
description: "Use when analyzing token costs from synchronized larch run logs for `--skill=design|implement`: price token reports, optionally plot trends, and print cost-reduction suggestions."
allowed-tools: Bash, Read
---

**MANDATORY: Follow the complete shared lifecycle contract in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle.md` with declared skill `report-tokens`.**

# Report Tokens

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Analyze token costs from synchronized larch run logs for the selected skill (`--skill=design|implement`) in the current Git repository. The CLI syncs once, scans the unpacked cache, reads the skill-specific token report JSON files, prices each run through `larch_core::report`, prints a markdown analysis, writes a durable NDJSON cache snapshot, writes the plot child's input, and optionally posts a GitHub `[Implement Analysis Report]` or `[Design Analysis Report]` issue.

For `--skill=implement`, reports carry no workflow dimension and graph/per-day trend output aggregates all runs into one `All runs` series/table set. For `--skill=design`, one aggregate report is generated. The filed issue intentionally omits raw per-issue JSON and actual-spend reconciliation unless `LARCH_REPORT_TOKENS_POST_ACTUAL_SPEND=1` is set.

Rate overrides: set environment variables documented in `docs/configuration-and-permissions.md` before invoking. See `docs/python-migration.md` for the migration playbook.

## Flags

Pass any of these after the skill name (for example, `/report-tokens --skill implement --no-issue`):

- `--skill <name>` (**required**): `design` or `implement`. Enum-validate before invoking the CLI; pass through to the module.
- `--no-issue` — skip posting the analysis report GitHub issue. `LARCH_REPORT_TOKENS_NO_ISSUE=1` has the same effect.
- `--no-plot` — skip plot generation; text analysis is still printed. `LARCH_REPORT_TOKENS_NO_PLOT=1` has the same effect.
- `--run-id <ID>` — flag reference: `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-id-flag.md`.

<!-- step:1 — Run analysis -->

Parse and validate `--skill` first. Reject missing or out-of-enum values before calling the CLI. Parse any `--no-issue`, `--no-plot`, or `--run-id <ID>` flags. The `--run-id` flag is consumed by the orchestrator and NOT forwarded to the CLI. Then:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" report-tokens analyze --skill "<name>" --operator-invoked [FLAGS]
```

where `[FLAGS]` are only `--no-issue` and/or `--no-plot`; `--run-id` is never included. `--operator-invoked` authorizes the analysis-report issue write, because `/report-tokens` is a direct operator-requested command; omit it with `--no-issue`, which posts nothing.

Verify the CLI exited successfully. On a normal run, stdout includes `## Report Tokens Analysis` plus `Cache JSON: <path>`. If it exits non-zero, stop and surface the error; do not invent partial cost results.

<!-- step:2 — Render plots -->

Skip this step when `--no-plot` was passed or `LARCH_REPORT_TOKENS_NO_PLOT` is set; the analysis text is already complete without it.

Otherwise read the `Plot input written to:` path from step 1 and render the PNGs. The plot child is the only `/report-tokens` helper that needs matplotlib, so it runs here rather than inside the Rust CLI:

```bash
PLOT_DIR="$(dirname "<plot-input-path>")"
MPLCONFIGDIR="$PLOT_DIR/mpl" python3 "${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/plot-cost-over-time.py" "<plot-input-path>" "$PLOT_DIR"
```

The child prints a JSON list of absolute PNG paths. Report those paths to the operator. A non-zero exit or unparseable output is not fatal: report that no plots were generated and keep the text analysis. Contract: `${CLAUDE_PLUGIN_ROOT}/skills/report-tokens/scripts/plot-cost-over-time.md`.

Advertised `Cache JSON:`, plot-input, and plot paths remain on disk after CLI exit and expire through automatic SessionStart `cleanup run` age sweeps for `larch-*` paths, rather than growing without bound.

## NEVER

1. **NEVER treat dollar output as billing truth.** The CLI uses transparent default rates and prints them with the analysis because vendor pricing and model routing can drift outside larch's control.
2. **NEVER forward removed replot flags.** Re-run against the synchronized cache instead.
