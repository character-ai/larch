### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Readable zero-heading ballots should fail closed
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `python/larch/review/review_core_body.py` treats readable but non-empty ballots with no headings as zero findings, which can let corrupt or truncated ballots skip voting instead of being treated as read failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

