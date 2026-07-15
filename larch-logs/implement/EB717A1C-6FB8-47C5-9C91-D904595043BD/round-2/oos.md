### FINDING_3: [OUT_OF_SCOPE] Direct detector syntax errors are uncaught
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Direct `detect()` callers can receive an uncaught `SyntaxError` for malformed Python documents, bypassing the `syntax_policy` path used by `run_rule`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Tokenization errors discard pragma suppressions
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `TokenError` can produce an empty pragma-comment map, causing false positives when declaration suppressions are present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Committed baseline file is missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The committed grandfathered baseline is absent, so CI and `make lint` use absent-baseline semantics and cannot exercise baseline freshness or byte-identity acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Golden identity tuple omits occurrence data
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Golden equivalence checks omit `pattern_name` and `occurrence`, so some occurrence-key regressions could evade fixture comparisons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Strict-stale precedence omits active findings
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: When stale rows and new violations coexist, strict-stale mode reports only stale diagnostics; this is shared, pre-existing engine behavior rather than a port-specific change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
