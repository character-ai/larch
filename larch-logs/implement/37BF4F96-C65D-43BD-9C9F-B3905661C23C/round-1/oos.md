### FINDING_13: [OUT_OF_SCOPE] Syntax findings bypass suppression
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-lint-engine-contracts
- **Severity**: minor
- **Concern**: Syntax-policy fail findings are returned before the suppression pass, so same-line suppression pragmas cannot suppress parse failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-lint-engine-contracts: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Tokenization failures silently disable suppression
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `TokenError` during comment tokenization produces an empty suppression map, silently skipping suppression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Path validation duplicates centralized helpers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Discovery reimplements containment validation already centralized in `larch.io`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Discovered symlink rejection lacks coverage
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-lint-engine-contracts
- **Severity**: minor
- **Concern**: There is no test that a symlink returned by `git ls-files` is rejected during discovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-lint-engine-contracts: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Boolean line validation lacks a focused test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No test verifies that `line=True` is rejected by finding validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_18: [OUT_OF_SCOPE] Equivalence fixtures are absent
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Expected equivalence golden fixtures and `test_lint_engine_equivalence.py` are absent for this partition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_19: [OUT_OF_SCOPE] Runner exceptions bypass the exit contract
- **Reviewer(s)**: dyn-dyn-lint-engine-contracts
- **Severity**: minor
- **Concern**: Exceptions raised directly by an injected `Runner` are not caught by `run_rule`, potentially bypassing the documented exit-code contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-lint-engine-contracts: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
