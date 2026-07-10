### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: invalid explicit run IDs fall through to another identity
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Invalid explicit run IDs are silently ignored, after which fallback identity resolution can bind the operation to a different persisted or hash-derived run identity than the caller requested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
