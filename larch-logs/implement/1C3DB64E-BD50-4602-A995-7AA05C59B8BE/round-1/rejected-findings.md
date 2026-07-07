### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Resume checks happen after routing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Resume preconditions are validated after the route command starts, so a missing `SESSION_ID` or unrecoverable `ISSUE_NUMBER` can still reach the router before the step aborts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Validate recoverable SESSION_ID and numeric ISSUE_NUMBER immediately after early gap-fill and before subprocess.run(route_cmd); add a test expecting zero route invocations on failed recovery.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Resume tests miss stale-sidecar and fail-closed cases
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The new tests cover the happy path, but they do not exercise verbal stale-sidecar recovery or the fail-closed resume paths that should stop before routing or refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add tests for verbal+stale route-state and for missing SESSION_ID / failed write-design-env abort paths.
  - From cursor-specialist-testing: Add parametrized fail-closed resume tests asserting rc 1, no ROUTE=resume@ stdout, and no design route or refresh when recovery preconditions fail.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

