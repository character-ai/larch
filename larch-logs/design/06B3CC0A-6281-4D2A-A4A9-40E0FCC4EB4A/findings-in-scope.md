### FINDING_1: Absolute cli.py argv capture
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The shim interception in `python/tests/review/test_review_and_fix.py` can miss the real `review-and-fix step5` invocation because the wrapper passes an absolute `python/cli.py` path in `argv[1]`. If the test keys off a literal `python/cli.py` token instead of the actual argv layout, it may delegate to the real loop, hang, flake, or miss `DIFFICULTY_OVERRIDE` forwarding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Match review-and-fix step5 when argv has review-and-fix at index 1 and step5 at index 2 after the cli.py path (or when argv[1].endswith("python/cli.py")), then assert flags on that captured slice only.

### FINDING_2: Clear STEP5_HANDOFF_READY_TO_COMMIT in resume harness
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The `skills/implement/scripts/step-5-resume.sh` test harness can inherit `STEP5_HANDOFF_READY_TO_COMMIT` from the parent environment, which may send execution down the commit route even without `--ready-to-commit`. That can skip the `review-and-fix` argv path the test is trying to exercise, leaving the captured argv empty or the wrapper exiting non-zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: test_implement_dispatch.py already delenv's this key; mirror that in the helper env (e.g. STEP5_HANDOFF_READY_TO_COMMIT=false or omit it) for every step-5-resume.sh invocation.
