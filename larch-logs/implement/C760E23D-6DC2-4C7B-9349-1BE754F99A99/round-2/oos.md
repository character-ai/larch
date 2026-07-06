### FINDING_9: [OUT_OF_SCOPE] Missing mirror tests for design persistence
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Mirror tests for persisting design-assessment invariants are missing, leaving additive persistence coverage incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add guideline-parity persist tests when touching design persistence


Vote tally: YES=1 NO=1 JUDGE_ERROR=1 Result=neutral Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Invariant audit config is not documented separately
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The run-log docs only mention the guideline cutover constant, so invariant audit configuration is not documented separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Document INVARIANT_SHIP_OUTCOME_MIN_LARCH_VERSION separately


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Ship-side invariant mirror coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The structural mirror for ship-side invariant handling is incomplete beyond the tested surfaces, so parity gaps could accumulate before the full matrix lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Finish flush and pytest matrix in one follow-up
Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

