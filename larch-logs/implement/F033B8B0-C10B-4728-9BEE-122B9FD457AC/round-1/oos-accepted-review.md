### FINDING_10: [OUT_OF_SCOPE] architecture: .claude/skills/release/scripts/release-finish.md:18-19
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] mergeCommit.oid missing falls back to origin/main tip when plugin.json version matches. Running finish before mergeCommit is populated could tag main tip instead of squash merge OID. Pre-existing contract; out of Phase 4 scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


