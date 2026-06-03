### FINDING_1: Missing ship driver acceptance coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-handback-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` covers only a small mocked subset of the planned driver acceptance matrix, leaving draft/forked/repo-unavailable/transient/CI handback/goto-rebase/cap-exhaustion/stall/JSON-routing regressions unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-handback-output.txt, dyn-ci-harness-output.txt: Address the concern above.



### FINDING_26: finalize.py unit coverage is incomplete versus the plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` lacks planned postbump/postmerge/teardown matrix cases, leaving session guard, cleanup, and branch rename behavior under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.



### FINDING_28: run_ship lacks idempotent phase re-entry
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Reinvoking Python `run_ship()` after handbacks starts from checks/postbump instead of resuming near the current PR/CI/merge phase, and can unnecessarily rerun rebase/push work against an open PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.



### FINDING_29: CI loop counters reset on every Python process
- **Reviewer(s)**: dyn-state-machine-output.txt, dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: CI iteration/rebase/fix/transient counters are local variables reset on each `run_ship()` invocation, so Step 8+ reinvokes can exceed bash’s session-wide caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt, dyn-ci-handback-output.txt: Address the concern above.



### FINDING_32: Python rebase-conflict handoff lacks bash-compatible fields
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python rebase conflicts surface only as JSON detail, without `CONFLICT_FILES`/handoff fields required by the documented conflict-resolution procedure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.



