## Goal
Flag step-duration outliers in timing-report.sh --full output so hung-session rows are clearly identified.

## Goal
Flag step-duration outliers in `timing-report.sh --full` output so hung-session rows are clearly identified and operators understand which steps inflated the report rather than seeing silently skewed statistics.

## Implementation Plan

### Problem
`render_report` in `scripts/timing-report.sh` computes each step's duration as `e - s` (end − start epoch seconds). When a Claude session hangs (laptop closed, network timeout, etc.), the interval between two marks can span many hours. The table shows these rows verbatim, giving totals like "12h 47m" for a single step with no indication that the value is anomalous.

### Approach
Add an outlier threshold (default: 14 400 s = 4 h, configurable via `LARCH_TIMING_OUTLIER_THRESHOLD_S`) passed into the AWK renderer as `-v outlier_threshold=...`. In the per-step loop, when `e - s > outlier_threshold`, suffix the duration cell with `[OUTLIER]` and accumulate the step name. After the `**Total**` row, if any outliers were collected, emit a single note line listing them. No changes to `--summary` or `--terse` modes (they report elapsed since the last mark, which is unambiguous real time). No changes to the timing ledger schema (the issue asks to *optionally* add a `timeout` status — the report-side flag is the minimal useful fix; ledger-side status is deferred).

### Files to edit

1. **`scripts/timing-report.sh`**
   - In the `render_report` bash call that invokes `awk`, add `-v outlier_threshold="${LARCH_TIMING_OUTLIER_THRESHOLD_S:-14400}"` before the heredoc-start `'`.
   - Inside the AWK `END` block, per-step loop (currently around line 193 for implement marks, and around line 204 for the fallback non-implement path):
     - After computing `e - s`, check `if ((e - s) > outlier_threshold)`: if true, append step name to `outlier_steps[]` / `outlier_count++`, and use `hms(e - s) " [OUTLIER]"` in the table cell instead of plain `hms(e - s)`.
   - After `print "| **Total** | | " hms(total_duration) " |"`, add:
     ```awk
     if (outlier_count > 0) {
       msg = ""
       for (oi = 1; oi <= outlier_count; oi++) {
         if (oi > 1) msg = msg ", "
         msg = msg outlier_steps[oi]
       }
       print ""
       print "(*Outlier steps: " msg " — duration exceeds " hms(outlier_threshold) " threshold; may reflect hung sessions.)"
     }
     ```
   - Apply the same outlier check inside `emit_child_rows` for design/review child rows.

2. **`scripts/timing-report.md`**
   - Under "Duration rules" / "Full reports", add a note documenting `LARCH_TIMING_OUTLIER_THRESHOLD_S` (default 14 400 s = 4 h) and that steps exceeding it are marked `[OUTLIER]` in the table with a trailing note.

3. **`scripts/test-timing-report.sh`**
   - Add a test fixture with one implement step having duration > 4 h (e.g., marks at epoch 0 and 50 400 = 14 h apart). Verify:
     - The output contains `[OUTLIER]` for that step.
     - The outlier note line appears after the Total row.
     - A step with duration < 4 h does NOT get the `[OUTLIER]` tag.
   - Also add a short test to verify `LARCH_TIMING_OUTLIER_THRESHOLD_S` overrides the default (set threshold to, say, 100 s so a 2-minute step triggers it).

### Edge cases
- `outlier_threshold <= 0`: guard with `if (outlier_threshold <= 0) outlier_threshold = 14400` in the AWK `BEGIN` block to prevent every step from being flagged.
- Child (design/review) rows: checked in `emit_child_rows` with the same threshold, flagged independently.
- `--summary` and `--terse`: no change needed; they report overall elapsed, not per-step intervals.
- The `**Total**` row still shows the true wall-clock span (subtracting outlier intervals would misrepresent when the run actually occurred).

### Test plan
1. Run `scripts/test-timing-report.sh` after changes — must print `PASS: test-timing-report.sh`.
2. Run `/relevant-checks` to verify pre-commit and agent-lint pass.
3. Visually confirm the new test fixture produces `[OUTLIER]` in the rendered table and the trailing note.
