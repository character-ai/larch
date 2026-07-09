### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:313-337
- **Concern**: Design OSError recovery still appends issue detail after summary and skips review detail. Scenario: The plan edge case requires prefix detail before degraded summary, but the file also says keep the existing degraded issue-detail path. The except OSError handler re-reads out_file and calls _append_issue_detail, which keeps summary first. On write failure after assembly, the correctly ordered in-memory body is discarded. Review detail is never added on this path.
- **Proposed resolution**: Refactor the except handler to reuse the same prefix-join assembly as the success path (review detail, then exec issues, then summary_body), fail-soft per section, then write once. Drop _append_issue_detail there. Add or extend a write-failure test to assert prefix-before-summary ordering when enrichment write fails.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/report/test_final_report.py:421-442
- **Concern**: Implement tests omit exec-issues-before-marker ordering guard. Scenario: The design test plan requires ## Exec Issues and Warnings before <!-- larch:run-summary v=1 -->, but the implement test plan only checks review detail ordering. An implementer could move review detail and leave exec issues appended after the summary block, partially defeating the feature.
- **Proposed resolution**: Add index ordering assertions to test_write_final_report_appends_exec_warning_detail_to_summary_and_run_log (and optionally the review-timing test when both sections exist): exec issues and review detail must both precede the summary marker. ## Findings ### 1. correctness — `python/larch/design/design_summary.py:313-337` The plan’s edge cases require prefix detail before a degraded summary, but the `design_summary.py` update also says to keep the existing degraded issue-detail path unchanged. Those two instructions conflict. Today’s `except OSError` block re-reads `out_file` and calls `_append_issue_detail`, which appends after the summary. On a write failure after in-memory assembly, the correctly ordered body is thrown away. Review detail is never added on this path. **Suggested revision:** Make the except handler reuse the same prefix-join logic as the success path, then add a write-failure test that asserts prefix-before-summary ordering. ### 2. risk-integration — `python/tests/report/test_final_report.py:421-442` The design test plan guards exec-issues ordering before the summary marker. The implement test plan only guards review-detail ordering. A partial implement could move Gantt content above the summary while leaving exec issues below it. **Suggested revision:** Add marker-order assertions to `test_write_final_report_appends_exec_warning_detail_to_summary_and_run_log`. --- **Assessment:** The plan is appropriately minimal: two assembly sites, no renderer changes, prefix-then-summary join. The main gap is the unstated `except OSError` branch in `_write_enriched_post_publish_summary`, which the success-path refactor alone will not fix.

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/final_report.py:799-846; python/larch/design/design_summary.py:301-308
- **Concern**: Moving the whole run-summary block behind the detail sections breaks the first-line contract that downstream tolerance code reads.. Scenario: run_log_tolerance.final_summary_terminal_heading() and stale_bail_heading_with_pr_evidence() key off the first nonempty line of final-summary.md, so real bailed/stalled/design-only runs will stop matching the skip signal once review or issue detail becomes line 1.
- **Proposed resolution**: Either keep a lightweight run-summary heading first, or update run_log_tolerance to locate the terminal run-summary heading anywhere in the file before evaluating it.

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:313-334
- **Concern**: The write-failure recovery path still rewrites the degraded file as summary then detail, and it drops the review detail entirely.. Scenario: If enriched-summary writing hits the OSError fallback, the published final-summary.md will keep the old order and omit the review prefix, so the degraded path no longer matches the new contract.
- **Proposed resolution**: Rebuild the recovery branch with the same prefix order as the success path, including the review detail, before writing degraded_body back out.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:313-334
- **Concern**: Design enrichment write-failure handler conflicts with degraded prefix-order edge case. Scenario: Edge cases require prefix detail before the degraded summary, but the plan also says to keep the existing degraded issue-detail path. The OSError handler at 322-334 re-reads stale on-disk summary and uses _append_issue_detail, which postfixes issue detail and drops any in-memory review detail assembled in the try block when write_text fails.
- **Proposed resolution**: Refactor the except OSError branch to reuse the same prefix-join assembly as the happy path (review detail, issue detail, then summary_body), retry writing that body, and add a focused test (e.g. extend test_render_final_summary_write_failure or a new enrichment-failure case) asserting detail sections precede the summary marker.

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-Report Order Regression
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:300-334
- **Concern**: Degraded recovery still rebuilds from the summary-only file and appends issue detail after it.. Scenario: If `_write_enriched_post_publish_summary` hits its OSError branch, the fallback output keeps the run-summary block first and drops any rendered review detail, so the new detail-before-summary contract regresses on the degraded fallback path.
- **Proposed resolution**: Rebuild the recovery body with the same prefix-first join, or reuse the already assembled review and issue prefix before writing the degraded summary.
