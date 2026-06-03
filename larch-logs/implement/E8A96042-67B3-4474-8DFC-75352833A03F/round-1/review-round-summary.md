# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (1 exonerated)

## Accepted Findings

### FINDING_2: Exit-2 STEP_FAILED harness coverage is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-exit2-streams-output.txt
- **Severity**: important
- **Concern**: `test-implement-bootstrap-invoke.sh` covers only a subset of handled `STEP_FAILED` exit-2 cases and incompletely checks stderr/stdout/redaction behavior. Regressions in operator messages, empty stdout discipline, or secret redaction could ship without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-exit2-streams-output.txt: Address the concern above.


### FINDING_4: Usage-error harness cases are missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The wrapper harness does not cover absent `--mode`, invalid/missing mode usage exits, and resume without `IMPLEMENT_TMPDIR`, so usage-contract regressions can slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: Structural pins do not enforce `set +e`/`set -e` adjacency
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Structure tests count `set +e`/`set -e` occurrences globally rather than pinning them immediately around each `implement-bootstrap-invoke.sh` command and `_inv_rc=$?` capture. A future edit could break the fence while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Initial-mode unset coder behavior is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness lacks a case proving initial mode omits `--coder` when coder is unset, so the wrapper could regress to passing an empty `--coder` and disrupt coder selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


