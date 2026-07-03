### FINDING_3: Temp python3 shim needs executable, pinned bootstrap
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The temp `python3` stub is not robustly bootstrapped, so the wrapper may fail before argv capture or recurse through `PATH` instead of invoking the intended interpreter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror `python/tests/review/test_plan_review_panel.py::_write_python3_agent_stub`: write the shim with `#!{sys.executable}`, `chmod 0o755`, store `REAL_PYTHON=sys.executable` before `PATH` mutation, delegate with `os.execv`.
  - From Cursor-Requirements: Add stub.chmod(0o755) in the helper, matching python/tests/review/test_plan_review_panel.py _write_python3_agent_stub.


