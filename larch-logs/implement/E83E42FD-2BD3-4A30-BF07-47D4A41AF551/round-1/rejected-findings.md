### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Normalize-status coverage should prove bgjob wins over legacy and pin bgjob helpers
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The unit coverage around normalize-status is still too narrow to catch a revert that prefers legacy env state over the bgjob path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: `Extend static contract pins or add normalize-status test asserting BGJOB_RC_KEY and bgjob path helpers.`
  - From cursor-specialist-testing: `Add a normalize-status test with divergent env files asserting bgjob wins.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

