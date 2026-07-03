### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/git/merge.py:103-121
- **Concern**: Plan excludes merge.py, but persistent mergeStateStatus=UNKNOWN still bypasses the proposed CI_NOT_READY wait path. Scenario: If GitHub keeps mergeStateStatus=UNKNOWN through MERGE_PR_INITIAL_UNKNOWN_RETRIES while checks are pending, merge_pr returns MERGE_RESULT_ERROR before ship.py sees MERGE_RESULT_CI_NOT_READY; the run stalls at merge and never re-loops to the later admin-merge fallback
- **Proposed resolution**: Extend the plan with a minimal merge.py change and focused test: after UNKNOWN retries, return MERGE_RESULT_CI_NOT_READY when PR checks are not all passing, while preserving the existing ERROR for UNKNOWN when checks are passing or cannot justify a CI wait
