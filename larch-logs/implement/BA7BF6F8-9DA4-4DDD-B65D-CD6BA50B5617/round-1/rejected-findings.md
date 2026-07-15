### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Equivalence fixtures bypass the engine adapter
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Equivalence fixtures use `scan_file` rather than `lint.detect` or `run_rule`, so regressions in the engine-backed integration can go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
