### [rejected] FINDING_16

### FINDING_16: correctness: scripts/lib-vote-tally.sh:37-38
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] reviewer_for_block only accepts case-sensitive canonical bold labels with an immediately attached colon. Variants like '- **Reviewer** : Name' or lowercase '- **reviewer**:' yield unknown and mis-attribute score rows despite a present reviewer line. Allow optional whitespace before the colon and/or case-fold the Reviewer(s) token for the bold branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

### FINDING_18: risk-integration: scripts/test-lib-vote-tally.sh:117-126
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Embedded-colon false positive covered only via **Concern** line Still valid for the bug class; slightly narrow vs arbitrary prose lines Add an extra block where a non-field prose line contains Reviewer: mid-line if you want broader regression lock-in
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

