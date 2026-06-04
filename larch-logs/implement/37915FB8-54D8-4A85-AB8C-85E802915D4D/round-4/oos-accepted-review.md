### FINDING_12: [OUT_OF_SCOPE] Limit counts directories instead of parseable runs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: `LARCH_REPORT_TOKENS_LIMIT` is consumed by every run directory, including empty/invalid ones, so a limit can stop scanning before later valid runs are parsed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scan-pipeline-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


