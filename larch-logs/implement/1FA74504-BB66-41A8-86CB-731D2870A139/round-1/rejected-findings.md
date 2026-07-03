### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Skip out-of-scope rows before merging identities
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: JSONL parsing can let `out_of_scope` rows survive into identity merging, which can replace earlier accepted rows and distort realized-tier counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Preserve escalations when rating validation fails
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: If `difficulty-rating.json` exists but fails `applied_tier` validation, escalation evidence is ignored and the realized tier can become unknown instead of HARD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Materialize runs even without rating or classification sources
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Runs with both rating and classification sources absent can disappear entirely instead of being counted as unratable, which under-reports corpus totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Always materialize a RunRecord for safe child dirs and keep exclusion only at the matrix gate


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

