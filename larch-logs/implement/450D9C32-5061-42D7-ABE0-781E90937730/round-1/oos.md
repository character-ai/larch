### FINDING_11: correctness: scripts/test-ship-pr.sh:769-785
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness pr_create_flush still expects post-create larch-log manifest pr_number plus commit. run_pr_create_phase no longer calls larch-log manifest for pr_number; ship-pr test harness fails on grep for manifest + commit. Update stub expectations and test narrative to match pre-PR commit-only flow or remove manifest assertion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_16: risk-integration: scripts/ship-pr.md:70,scripts/ship-pr.md:95-98
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Authoritative ship-pr.md still documents post-create manifest write log commit and push-before-CI-wait for final-summary. Operators and reviewers follow stale contract; debugging pr-create ordering against docs yields wrong conclusions. Rewrite invariant and Log Refresh sections to match scripts/ship-pr.sh pre-PR write-final-report optional pre-PR commit create-pr push and best-effort post write-final-report.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:965-967 skills/implement/scripts/write-final-report.sh:51-54
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Possible RUN_ID mismatch between ship-pr flush_run_id and write-final-report RUN_ID resolution. If parent-issue RUN_ID and ship-pr-state RUN_ID diverge, final-summary could be written under a different implement run directory than the one committed. Pre-existing class of issue; unchanged ID-resolution split vs prior manifest+commit pairing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

