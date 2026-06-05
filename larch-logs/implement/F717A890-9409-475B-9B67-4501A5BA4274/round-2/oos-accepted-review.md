### FINDING_12: [OUT_OF_SCOPE] Open-pr resume can bypass leftover security/OOS sidecar material
- **Reviewer(s)**: dyn-github-pr-output.txt
- **Severity**: latent
- **Concern**: Open-pr resume skips `_materialize_manifest_oos` and the security sidecar unless `OOS_PENDING` is set, so leftover OOS/security observations from an interrupted fresh run may be bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-github-pr-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


