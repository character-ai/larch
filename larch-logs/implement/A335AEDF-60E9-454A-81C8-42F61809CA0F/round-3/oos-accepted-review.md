### FINDING_10: [OUT_OF_SCOPE] correctness: scripts/dispatch-with-waterfall.sh:275-278
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] cap_hit bypasses require-result-pattern (pre-existing). Cap-hit without headings reaches validator as validation-failed not dispatcher retry. Track under #2895; out of scope for this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_6: [OUT_OF_SCOPE] code-quality: SECURITY.md:133
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Branch mixes unrelated ADOPTED sentinel hardening with #2881 aggregator work. Revert or bisect of one concern affects unrelated security/docs changes. Split #2878 hardening into separate PR or commit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


