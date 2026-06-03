### FINDING_3: [OUT_OF_SCOPE] write-after rollback semantics documentation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: write-after rollback uses `write-cursor --value ROUND_NUM` with count decrement only on success. Pre-existing cursor/count semantics; the failure path warns but remains hard to reason about relative to the state machine.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

