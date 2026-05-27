### FINDING_3: Successful recovery dispatch may not clear stall tracking
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Recovery dispatch success lacks an explicit transition to the step that clears `STALL_TRACKING`, so teardown can still treat a merged recovery as stalled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.



