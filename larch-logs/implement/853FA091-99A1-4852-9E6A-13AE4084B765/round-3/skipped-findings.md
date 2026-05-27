### FINDING_3: Review-round counter persists after tally errors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The counter write excludes only `panel-failed`, so `tally-error`, empty status, or other non-success states can still consume a capped review round even though Gate B artifacts may be incomplete or degraded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.



