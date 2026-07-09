### FINDING_4: [OUT_OF_SCOPE] probe-failure skip can hide real-process coverage
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The harness exits 0 on probe failure, so restricted-sandbox CI can report success without running real-process scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] `wait_done_rc` can accept malformed CLI output
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `wait_done_rc` uses substring matching for `DONE` and `BGJOB_RC`, so malformed multi-line CLI output could match without a valid result envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

