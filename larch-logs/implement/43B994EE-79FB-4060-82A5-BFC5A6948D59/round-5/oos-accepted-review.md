### FINDING_11: [OUT_OF_SCOPE] correctness: scripts/promote-release.sh:79
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Multi-line CURRENT_LATEST when multiple isLatest releases exist. Two Latest flags could break promote string compare (pre-existing). Use jq -r '.[0]' after filtering or fail on count != 1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


