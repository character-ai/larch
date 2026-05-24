### FINDING_7: [OUT_OF_SCOPE] Pre-existing two-directory trap gap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-read-design-review-budget-invoke.sh:47-63` already had a pre-existing two-directory cleanup trap gap for `dt` and `full_dt`; the in-scope version is the amplified four-directory gap captured above.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

