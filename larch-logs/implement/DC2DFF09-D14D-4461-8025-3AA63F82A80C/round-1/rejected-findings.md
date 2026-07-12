### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Composed marker strings evade detection
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: The AST scan misses concatenated strings and f-strings, allowing contributors to reconstruct marker grammar without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Direct or aliased helper imports evade detection
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Helper detection recognizes only bare `issue_wire.<helper>` calls, so direct imports or aliases can satisfy runtime behavior while failing the ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Missing-helper tests cover only one required helper
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Regression tests exercise only the missing `design_router.py` helper path; removals of `compose_named_block` or `named_block_marker_re` from other consumers could go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Helper calls do not validate marker arguments
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The ratchet checks helper callees but not required `marker="plan"` or `kind="start"` arguments, so calls with incorrect routing values can pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Grammar-owner exclusion lacks a regression test
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The exclusion of `issue/issue_wire.py` from the scan is untested, so an incorrect grammar-owner path could produce false positives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
