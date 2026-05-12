## Goal
Fix the plot_dir NameError bug in the matplotlib subprocess, add auto GitHub analysis report issue creation, and add three new flags (--no-issue, --no-plot, --plot-from) to /report-tokens.

## Implementation Plan
All changes in `skills/report-tokens/scripts/run-analysis.sh` (+ sibling `.md`).

1. **Fix plot_dir NameError**: Pass `plot_dir` as `sys.argv[2]` into the embedded subprocess script; add `plot_dir = sys.argv[2]` before the plotting loop.
2. **Bash flag parsing**: After `--help`, parse `--no-issue`, `--no-plot`, `--plot-from N`; export as env vars for Python.
3. **--no-plot support**: Early return in `plot()` when `LARCH_REPORT_TOKENS_NO_PLOT` is set.
4. **Auto-issue creation**: Capture `print_analysis()` output; call `gh issue create` with timestamped `[Analysis Report]` title + raw per-issue JSON block.
5. **--plot-from mode**: `load_raw_records()` extracts JSON from prior report body; `main()` detects `--plot-from` argv and calls `plot()` only.

## Test plan
Run `/relevant-checks` (pre-commit on modified files + agent-lint).
