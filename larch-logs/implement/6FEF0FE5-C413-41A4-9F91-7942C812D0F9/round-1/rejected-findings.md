### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: Child-mode stale-Python guard coverage is missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The child-mode stale-Python guard failure path is no longer pinned, so a bgjob-child regression could slip through without exercising the rc 4 sidecar behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Restore a --bgjob-child test that fails the guard via larch-run and asserts rc 4 sidecars without invoking ship pr.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

