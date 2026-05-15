## Goal
Add per-day cost trend tables to /report-tokens (8 tables: 4 vendors × SIMPLE/HARD)

## Implementation Plan

### Goal
Add per-day cost trend tables to run-analysis.sh so every [Analysis Report] issue includes 8 markdown tables (4 vendor buckets × 2 workflow types).

### Changes to skills/report-tokens/scripts/run-analysis.sh

#### 1. Bash scanning section (3 jq invocations, lines ~130-207)
- Extract `started_at` from each manifest: `started_at=$(jq -r '(.started_at // "") ' "$manifest" 2>/dev/null)` 
- Add `--arg startedAt "$started_at"` to each of the 3 jq -cn calls
- Add `startedAt: $startedAt` field to each emitted JSONL object

#### 2. Python analyzer (within the heredoc)
- In `analyze()`: extract `started_at_date = parse_date(issue.get("startedAt"))` and store in each record dict
- Add new `per_day_trend_tables(records)` function:
  - For 4 vendor buckets: total, claude, codex, cursor
  - For 2 workflows: SIMPLE, HARD
  - Group records (with workflow in {SIMPLE, HARD} and started_at_date not None) by `started_at_date.date()`
  - Compute per-day: N, median, mean, P75 (manual: sort values, take index at floor(0.75 * N)), max, total
  - Format as markdown table: `| Date | N | Median | Mean | P75 | Max | Total |`
  - Mark N=1 rows with `*` (and add footnote `_* single-run day — statistically limited_`)
  - Return multi-section markdown string

- Update `print_analysis()`: call `per_day_trend_tables(records)` and print the output after the existing sections

- Update `load_raw_records()`: add `started_at_date = None` to each record (trend tables unavailable in --plot-from mode)

### Testing strategy
- Run `make lint` (pre-commit + agent-lint) to verify no regressions
- Run the analyzer manually against the local larch-logs directory with `--no-issue` to verify table output

### Edge cases
- No SIMPLE or HARD runs for a day: table row is absent
- All runs for a day have N=1: each row gets asterisk footnote
- Vendor has 0 cost for a day: still included in the row
- Empty records list: per_day_trend_tables returns empty string (no section added)

## Test plan
(no test plan section in plan-file)
