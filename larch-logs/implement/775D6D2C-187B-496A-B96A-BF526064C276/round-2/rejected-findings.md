### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Zone names are not safely validated for wire output and query construction
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Zone names containing newlines can corrupt the `RESOLVED_SEARCH` wire output, while unvalidated zone tokens can alter the GitHub OR query and broaden mining beyond the intended zones.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Reject \n and \r in parse_zones and add a pytest negative; align with G-IO-2 wire-value handling.
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Prose-only validation can borrow evidence from adjacent clusters
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Validation scans a broad character window instead of the containing cluster or proposal block, allowing a marker to pass by borrowing citations or mechanical-alternative text from a neighboring cluster.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Parse cluster or proposal boundaries and validate each marker only within its own block; add an adjacent-cluster negative fixture.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Mechanical-alternative validation accepts incidental keywords
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The mechanical-alternative regex accepts incidental mentions of words such as “lint,” “hook,” or “invariant,” allowing vague prose to satisfy the validation requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Require an explicit alternative line pattern instead of a bare keyword match


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Digest-size accounting omits JSONL separators
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `DIGEST_CHARS` sums serialized record lengths without JSONL newline separators, under-reporting multi-record digest sizes and potentially misleading token-budget warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Measure exact serialized JSONL bytes including separators
  - From cursor-specialist-testing: Compute DIGEST_CHARS from written digest.jsonl bytes and add a multi-record run_prepare length assertion.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Bare regression detection over-counts negated and test-context wording
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The bare regression regex matches phrases such as “non-regression,” “not a regression,” and “regression test,” inflating regression counts and the regression-ratio headline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Tighten bare-regression detection and add negated-context fixtures


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (0 YES)

### FINDING_13: Singular suggested-fix heading lacks a negative allowlist test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Tests cover `## Suggested fix(es)` but not the singular `## Suggested fix` heading, so regressions involving origin markers in the singular suggested-fix body may go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a singular suggested-fix-only negative fixture parallel to the suggested fix(es) test.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
