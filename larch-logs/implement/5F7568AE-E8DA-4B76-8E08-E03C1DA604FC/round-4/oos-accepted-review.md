### FINDING_10: [OUT_OF_SCOPE] architecture: skills/review/scripts/review-core.sh:501-518
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] main-agent-vote-required path still skips emit-tally. Observability gap versus zero-findings is pre-existing; this diff does not introduce it. Only if you want parity: emit a minimal summary on that exit path too.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected


### FINDING_11: [OUT_OF_SCOPE] code-quality: skills/review/scripts/review-core.sh:331-351
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] panel-failed path still skips emit-tally so no review-summary.json with panel. Pre-existing; not introduced by this diff. No action required for this branch unless product wants panel on threshold failure.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected


