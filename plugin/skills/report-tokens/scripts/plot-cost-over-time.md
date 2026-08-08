# plot-cost-over-time.py contract

`plot-cost-over-time.py` is the only `/report-tokens` helper that imports
matplotlib. Step 2 of `skills/report-tokens/SKILL.md` invokes it, reading the
input file that `report-tokens analyze` writes. Keeping the launch in the skill
is what lets the Rust CLI own the report without larch growing a general
arbitrary-script process class.

## Input schema

The first argv is a JSON file with:

- `version`: schema version, currently `1`.
- `skill`: `design` or `implement`.
- `series`: array of series objects.
  - `label`: display label.
  - `points`: array of `{date, cost}` objects where `date` is an ISO date string and `cost` is a number.

For `implement`, callers pass exactly one `All runs` series. For `design`,
callers pass `All runs` series. Future schema changes should bump
`version` and keep the old reader behavior until callers are cut over.

## Output and environment

The second argv is the output directory. The script writes PNG files there and
prints a JSON list of absolute PNG paths to stdout. The caller sets
`MPLCONFIGDIR` to a directory under the plot output root before spawning the
child process.
