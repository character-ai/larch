### FINDING_1: Degraded fallback drops review detail and keeps summary-first
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Codex-dyn-Report Order Regression
- **Severity**: major
- **Concern**: The `OSError` recovery path in `design_summary.py` rebuilds from stale summary-only content, appends issue detail after the summary, and discards the in-memory review-detail prefix, so the degraded write path violates the new prefix-before-summary ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Refactor the except handler to reuse the same prefix-join assembly as the success path (review detail, then exec issues, then summary_body), fail-soft per section, then write once. Drop _append_issue_detail there. Add or extend a write-failure test to assert prefix-before-summary ordering when enrichment write fails.`
  - From Cursor-Requirements: `Refactor the except OSError branch to reuse the same prefix-join assembly as the happy path (review detail, issue detail, then summary_body), retry writing that body, and add a focused test (e.g. extend test_render_final_summary_write_failure or a new enrichment-failure case) asserting detail sections precede the summary marker.`
  - From Codex-dyn-Report Order Regression: `Rebuild the recovery body with the same prefix-first join, or reuse the already assembled review and issue prefix before writing the degraded summary.`

### FINDING_2: Moving the summary table last can break first-line tolerance checks
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Printing the run-summary block or summary table after detail sections can move the first nonempty line away from the terminal summary heading, which breaks downstream tolerance logic that keys off that first line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: `Either keep a lightweight run-summary heading first, or update run_log_tolerance to locate the terminal run-summary heading anywhere in the file before evaluating it.`

### FINDING_3: Implement tests miss exec-issues ordering before the summary marker
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The implement test coverage only checks review-detail ordering, so a regression could still leave exec issues after the summary marker while passing the current assertion set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Add index ordering assertions to test_write_final_report_appends_exec_warning_detail_to_summary_and_run_log (and optionally the review-timing test when both sections exist): exec issues and review detail must both precede the summary marker.`
