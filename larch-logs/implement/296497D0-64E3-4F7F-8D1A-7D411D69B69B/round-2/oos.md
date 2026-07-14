### FINDING_5: [OUT_OF_SCOPE] Scan-only deduplication ignores symbol identity
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Scan-only deduplication can collapse distinct symbol-metric findings because symbol identity is not part of the key; this is pre-existing and outside the baseline work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
