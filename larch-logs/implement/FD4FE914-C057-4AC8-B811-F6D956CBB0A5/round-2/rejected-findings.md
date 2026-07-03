### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Empty deep queue still launches deep dispatch
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Stage 2 gates deep dispatch on a non-empty queue path string, but Python emits that path even when the queue has zero rows, so triage-only or fully cached runs can still launch the verifier and burn tokens on an empty queue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Gate on DEEP_PENDING>0 or non-empty queue contents; parse DEEP_PENDING from ledger stdout; skip deep launch when zero.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

