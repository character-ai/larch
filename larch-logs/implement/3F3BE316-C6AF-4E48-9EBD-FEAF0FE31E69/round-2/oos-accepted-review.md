### FINDING_1: [OUT_OF_SCOPE] Allowlist TSV can drift from runtime body composition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Allowlist TSV is lint-only and not tied to `compose_body_content`, so runtime issue/comment body fields can drift from the allowlist and leak consumer metadata until lint catches it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


