## Proposed Design Outline

### Goals
- Align `step-5-resume.sh` stall exit code with the Python dispatcher (exit 0 on `NEXT_ACTION=stall` when `commit_rc=0`).
- Remove the inconsistency callers observe between the shell and Python stall paths.

### Non-goals
- Changing behavior for other `NEXT_ACTION` values (`continue`, `*`).
- Modifying `dispatch_commit_route.py` or any Python code.
- Adding new stall-handling or retry logic.

### Approach sketch
- Change `exit 1` to `exit 0` in the `1:stall` case of `run_resume_worker()` in `step-5-resume.sh`.
- Add a test to `python/tests/review/test_review_and_fix.py` or a comparable location verifying the shell stall path exits 0.

### Surfaces in scope
- `skills/implement/scripts/step-5-resume.sh` (one-line fix)
- Test file for `step-5-resume.sh` stall behavior

### Open questions
- None.
