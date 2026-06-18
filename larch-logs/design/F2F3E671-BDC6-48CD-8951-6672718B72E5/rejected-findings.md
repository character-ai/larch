### [Plan Review] FINDING_1

### FINDING_1: design_lifecycle.py relevant-checks omits py-test
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan extends the `python/agents.py` `_DIRECT_TARGET_RULES` row to `py-test`, but the `python/design_lifecycle.py` row still routes only to `test-check-plan-size`. If Step 2b drafter dispatch moves into `design_lifecycle.py`, edits there will not run new `test_design_lifecycle.py` CLI-verb assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add py-test (or wants_py_test=true) to the python/design_lifecycle.py / python/test_design_lifecycle.py tuple alongside or instead of test-check-plan-size-only routing


