### FINDING_3: [OUT_OF_SCOPE] Direct detector syntax-error contract
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Direct `detect()` callers can receive an uncaught `SyntaxError` for malformed Python, unlike `run_rule`, which applies `syntax_policy`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Baseline serialization depends on first row kind
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `_serialized_baseline` derives its key policy from `rows[0]` while serializing sorted rows, which can be incorrect for mixed-kind input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Tokenization errors can drop pragma comments
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Tokenization errors silently discard the comment map used for declaration pragmas, potentially causing missed suppressions and false positives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] AST fallback can emit line zero
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Missing AST line numbers fall back to zero, potentially producing `path:0` findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Committed baseline is absent
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The committed baseline file is absent on `origin/main` although documentation and the plan reference it; this predates the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Equivalence ignores occurrence identity
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-occurrence-baseline
- **Severity**: minor
- **Concern**: Equivalence comparisons omit `pattern_name` and `occurrence`, so golden runs may not detect occurrence-identity regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-occurrence-baseline: Address the concern above.
Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false
