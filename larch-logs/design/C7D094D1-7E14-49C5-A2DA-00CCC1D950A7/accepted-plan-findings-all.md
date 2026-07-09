### FINDING_1: Late non-reserved reviewer row is not actually covered
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The regression test can pass even if the rendering logic still drops late-starting non-reserved reviewer rows, because reserved apply/fallback rows may mask the missing tail entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror `test_progress_vendor_rows_cap_without_apply_keeps_earliest`: use `PROGRESS_GANTT_ROW_CAP + 2` plain `codex-review` vendor rows with staggered starts and assert the latest-starting reviewer label (e.g. start `100 + over_cap - 1`) appears in the rendered `### Round 1 reviewer timing` chart


### FINDING_2: Coverage should hit the shipped final-summary path
- **Reviewer(s)**: Codex-dyn-Report Rendering Regression
- **Severity**: minor
- **Concern**: The regression is only exercised at a helper level, so a break in the committed final-summary entry points could still ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Report Rendering Regression: Add or move the regression into python/tests/report/test_final_report.py:97-136 and assert the >25-row chart appears in summary-final.md and final-summary.md from write_final_report


### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_progress_report.py:plan-test_render_phase_detail_gantt_shows_all_rows_when_over_cap
- **Concern**: The over-cap regression spec still allows a false pass when every vendor row shares one label. Scenario: Mirroring test_progress_vendor_rows_cap_without_apply_keeps_earliest reuses one output basename for all rows, so every row gets the same derived label. If cap=None is not wired, the chart can still show 25 copies of that label and an assertion on the latest-start label passes even though the two highest-start rows were dropped. Optional distinct basenames and optional row-count checks do not close that hole.
- **Proposed resolution**: Require per-index distinct output basenames (or another label-unique fixture) and assert the unique label for start 100 + over_cap - 1 is present. Also require a data-row count of at least PROGRESS_GANTT_ROW_CAP + 2 (lines with both │ and █). Apply the same mandatory guards to test_write_final_report_includes_uncapped_review_timing_gantt.

