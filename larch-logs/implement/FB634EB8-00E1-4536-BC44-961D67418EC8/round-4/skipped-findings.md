### FINDING_16: Planned finalize unit branches are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` lacks planned unit coverage for postbump force-push, remote checks, protected branch, verify-main suffix/mismatch, orphan reset, teardown rename, and larch-log guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



### FINDING_17: Planned ship integration branches are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` lacks planned coverage for postbump preflight, terminal phase failure, postmerge `phase=done` gating, partial-cleanup flush, sentinel writes, and skipped log-write status paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



### FINDING_18: Postmerge log recovery failure lacks fail-closed test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not assert that `flush_logs_post`/`finalize_postmerge_logs` skip manifest/report writes when `recovery_ok=false`, so future refactors could write `done` despite recovery failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.



