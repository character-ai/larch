### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Report sections appear in the wrong order
- **Reviewer(s)**: dyn-dyn-schema-provenance
- **Severity**: major
- **Concern**: `## Introduced risk` and `## Instance fixed, class open` are inserted before the Issues table instead of after it and before chronic zones, violating the report contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-schema-provenance: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_3: Introduced-risk sentinel validation is incomplete
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-schema-provenance
- **Severity**: minor
- **Concern**: Non-exact or whitespace-only introduced-risk values can be accepted and rendered as real risks instead of being normalized to or rejected as invalid `none found` values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-schema-provenance: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Persisted field types are silently coerced
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Invalid persisted current-schema types, such as a string `class_complete`, are silently coerced and can produce false class-open follow-ups. Persisted fields need type and coherence validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
