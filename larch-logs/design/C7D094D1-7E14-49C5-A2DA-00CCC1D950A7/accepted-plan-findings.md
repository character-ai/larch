### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_progress_report.py:plan-test_render_phase_detail_gantt_shows_all_rows_when_over_cap
- **Concern**: The over-cap regression spec still allows a false pass when every vendor row shares one label. Scenario: Mirroring test_progress_vendor_rows_cap_without_apply_keeps_earliest reuses one output basename for all rows, so every row gets the same derived label. If cap=None is not wired, the chart can still show 25 copies of that label and an assertion on the latest-start label passes even though the two highest-start rows were dropped. Optional distinct basenames and optional row-count checks do not close that hole.
- **Proposed resolution**: Require per-index distinct output basenames (or another label-unique fixture) and assert the unique label for start 100 + over_cap - 1 is present. Also require a data-row count of at least PROGRESS_GANTT_ROW_CAP + 2 (lines with both │ and █). Apply the same mandatory guards to test_write_final_report_includes_uncapped_review_timing_gantt.

