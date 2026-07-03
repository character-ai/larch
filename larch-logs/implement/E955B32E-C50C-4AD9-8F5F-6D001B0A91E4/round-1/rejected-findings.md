### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Real-git rebase fixture and production pin path are the regression signal
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: The test only remains a meaningful regression check if it keeps using a real base→feature→main-advance→rebase fixture and continues to exercise the production pin/invalidate path, with assertions that prove the post-rebase durable-note state rather than a mocked approximation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

