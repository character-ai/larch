### FINDING_3: [OUT_OF_SCOPE] Missing parity cases for version_already_published paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Python merge parity does not cover `version_already_published` paths exercised by `scripts/test-merge-pr.sh`, so Bash merge race behavior can drift without failing `py-test`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

