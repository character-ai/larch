# Review Round 2

- Mode: `diff`
- 5 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Implement legacy-label inventory is incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Implement has one inventory label despite emitting hundreds of assertion labels, and the one-directional audit cannot detect dropped or unregistered checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_3: Design legacy labels are not auditable
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Design inventory abbreviations do not match emitted failure strings, so parameterized failures cannot be reliably mapped to inventory labels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_5: Cross-file-bound predicate is unsupported
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: `cross_file_bound` is absent or unsupported while related fields remain unused, preventing pin tables from expressing and validating bounded cross-file contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: Adjacent-pair pins lack validation
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Adjacent-pair pins do not validate non-boolean non-negative expected counts or predicate-specific unit/comparator settings; negative counts can pass with zero matches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_7: Learn-from-bugs B.9 was not ported
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: The legacy B.9 prohibition on `mapfile`/`readarray` is absent from both the specialized port and inventory, allowing Bash-3.2-incompatible regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
