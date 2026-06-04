### FINDING_12: Step 2 lacks fail-closed test coverage for materializer failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test asserts that Step 2 bails out when the manifest has OOS observations but the materialization helper fails, risking a false `complete` status with no file triggers for Step 9a.1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: `ship-pr.sh` lacks runtime coverage for materializer failure forcing `OOS_PENDING`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After removal of prior ship-pr tests, materialize failure behavior is only grep-order covered; a non-empty manifest plus helper failure could skip `OOS_PENDING` and reach PR creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Security sidecar checkpoint blocking lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new `security-oos-observations.md` checkpoint block and Python pre-PR block lack regression tests, so security-routed manifest OOS could pass to PR creation or all-clear without SECURITY.md disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Accepted-OOS size checks can loop forever after Step 9a.1
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-flow-output.txt, dyn-shell-state-output.txt, dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Python and bash paths treat non-empty accepted-OOS markdown as requiring filing before checking whether disposition is already satisfied. Because accepted files remain after Step 9a.1, reinvocation can repeatedly return OOS filing or bounce between phases instead of reaching PR creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-flow-output.txt, dyn-shell-state-output.txt, dyn-python-parity-output.txt: Address the concern above.


### FINDING_18: Materializer contract markdown is not covered by header tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `materialize-manifest-oos.md` contract headers are not included in the reference-header test glob, so contract triplet drift can go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_20: Python `_oos_gate` does not enforce checkpoint ndjson preconditions
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Python calls `oos.disposition_ok` without enforcing the checkpoint rule that non-security accepted OOS requires a resolved `oos-issues.ndjson`, allowing Python-only disposition success paths that bash would fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.


### FINDING_3: OOS pipeline docs omit security sidecar and checkpoint stall semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Canonical OOS pipeline documentation does not fully describe `security-oos-observations.md`, private security handling, or the checkpoint behavior that refuses all-clear while that sidecar remains non-empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: Documented OOS dedup order differs from checkpoint order
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The documented cross-phase dedup order does not match the checkpoint accepted-file order, creating possible precedence confusion for implementers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


