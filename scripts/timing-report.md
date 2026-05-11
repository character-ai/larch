# timing-report.sh

`scripts/timing-report.sh` renders operator-visible timing summaries from the fixed-width TSV written by `scripts/timing-ledger.sh`.

Subcommands:

- `--since-last-mark --terse` prints one line for the latest mark whose skill matches `${LARCH_TIMING_SKILL:-implement}`:
  `Step name: elapsed=<HH:MM:SS> vendor-tasks=<N> (codex=<n>, cursor=<m>, gemini=<k>)`.
- `--summary` prints one grand-total line spanning all marks from the first to the present:
  `Total: elapsed=<HH:MM:SS> vendor-tasks=<N> (codex=<n>, cursor=<m>, gemini=<k>)`.
  Used as the default brief output in Step 17 when `LARCH_VERBOSE_TOKENS` is unset.
- `--full --markdown [--output FILE]` renders the full markdown report.
- `--append-timing-section FILE` renders the full report and idempotently replaces the block bracketed by `<!-- timing-report-begin -->` / `<!-- timing-report-end -->`.

Full reports include the latest workflow path (`HARD`, `SIMPLE`, or `unknown`), per-step durations, and vendor task averages by `(vendor, task_kind)`. Failed rows (`status != complete` or `exit_code != 0`) are excluded from averages and summarized below the table.

Duration rules:

- Implement marks are top-level rows when present.
- Design and review marks are nested under the implement interval in which their timestamp falls.
- Per-skill intervals are measured to the next mark of the same skill. The final mark of a skill runs until the latest workflow/vendor timestamp, or now.
- Total duration is the last implement mark minus the first implement mark when implement marks exist; otherwise it is the last mark minus the first mark.

The renderer is shell/awk-only and has no `jq` dependency. It skips rows whose first column is not `v1`, and warns to stderr when a `v1` row does not have exactly 13 columns.

Regression harness: `scripts/test-timing-report.sh` (sibling stub `scripts/test-timing-report.md`); wired into `make lint` via the `test-timing-report` Makefile target (shard `test-harnesses-4`).
