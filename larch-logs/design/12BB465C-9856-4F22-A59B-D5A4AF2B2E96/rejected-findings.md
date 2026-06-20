### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/collect_results.py:517-592
- **Concern**: [SCOPE-REDUCTION] OUTER_LAUNCHER_SITE retry replay is not required to fix #4886. Scenario: #4888 is initial launch failures logged as review Step 2; retries without meta site already fall back to launch-review default and that behavior is unchanged today. Adding RetryMeta.outer_launcher_site, _parse_meta wiring, _launch_outer_retry --site replay, and three collect_results tests expands the PR without a cited retry mislabel repro.
- **Proposed resolution**: Limit #4888 to threading --site into _review_append_launch_failure on first agent launch-review dispatch (plan_review_panel, review_and_fix/review_pipeline). Defer OUTER_LAUNCHER_SITE meta plus collect-results retry replay to a follow-up unless a live retry mislabel is filed.

