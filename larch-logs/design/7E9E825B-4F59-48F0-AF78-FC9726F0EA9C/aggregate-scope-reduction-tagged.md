### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements Phase2
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:9,124-147,196; python/test_ci_agentic_fix.py:1034-1082; python/ci_agentic_fix.py:398-403
- **Concern**: [SCOPE-REDUCTION] Plan maps OOS_3 to review_and_fix cleanup instead of the stated mixed mechanical rollback test. Scenario: The issue asks to cover the mixed mechanical rollback verify loop. The existing test uses one fixable job, so a bug that verifies only the first job could still pass. The plan spends OOS_3 scope on unrelated review_and_fix cleanup coverage.
- **Proposed resolution**: Replace the OOS_3 review_and_fix cleanup section with a two-fixable-job regression in python/test_ci_agentic_fix.py where one job verify fails. Assert rollback and delegate behavior. Touch python/ci_agentic_fix.py only if that test exposes a real bug.
