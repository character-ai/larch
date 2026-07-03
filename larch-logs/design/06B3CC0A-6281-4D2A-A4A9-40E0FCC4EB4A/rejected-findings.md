### [Plan Review] FINDING_2

### FINDING_2: Clear STEP5_HANDOFF_READY_TO_COMMIT in resume harness
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The `skills/implement/scripts/step-5-resume.sh` test harness can inherit `STEP5_HANDOFF_READY_TO_COMMIT` from the parent environment, which may send execution down the commit route even without `--ready-to-commit`. That can skip the `review-and-fix` argv path the test is trying to exercise, leaving the captured argv empty or the wrapper exiting non-zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: test_implement_dispatch.py already delenv's this key; mirror that in the helper env (e.g. STEP5_HANDOFF_READY_TO_COMMIT=false or omit it) for every step-5-resume.sh invocation.

