### FINDING_17: [OUT_OF_SCOPE] architecture: scripts/larch-log.sh:100
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Retry-suffixed dynamic Codex outputs are not in the explicit allow clause or larch-log.md enumeration. Retry shapes rely solely on broad *-output-*.txt patterns; narrowing that arm could drop retry forensics. Intentional per plan since no retry producers exist yet. Revisit when dispatch emits dyn-*-codex-output-retry*.txt; add explicit patterns and fixtures then.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_18: [OUT_OF_SCOPE] risk-integration: scripts/test-larch-log.sh:150-155
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No unit-level assert_round_artifact_included pins for dynamic Codex basenames. Integration-only coverage predates this branch; not removed by this diff. Extend assert_round_artifact_included when adding contract pins (see in-scope latent finding).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


