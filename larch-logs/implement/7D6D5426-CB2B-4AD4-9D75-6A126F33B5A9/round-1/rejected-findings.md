### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Scaffold-byte savings may not move the acceptance metric
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The rules-block compression mainly affects prompt/payload bytes because the relevant text is counted in `payload_base_bytes`; that can let Acceptance pass while `scaffold_bytes` barely changes, and there is still no automated byte/scaffold guard to enforce the stated density goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

