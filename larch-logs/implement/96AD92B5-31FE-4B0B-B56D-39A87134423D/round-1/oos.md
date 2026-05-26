### FINDING_16: [OUT_OF_SCOPE] architecture: skills/design/scripts/dispatch-plan-review-panel.sh
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Other dispatch-with-waterfall parents lack defensive unset LARCH_PAIRED_PID_FILE. Future nested helper call under inherited env could clobber PID file per test 27 semantics. Unset at waterfall entry or in every synchronous parent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] risk-integration: scripts/lint-foreground-markers.sh:1379-1397
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Linter does not enforce parent unset before nested DENYLIST children. Future nested script adds larch_quiet_write_paired_pid_file without parent unset; file holds short-lived child PID; parent survives monitor timeout (test 27 scenario). Extend lint or add shell-level test that top-level writers unset before nested exec paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] architecture: SECURITY.md:156-166
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Single-PID signaling does not tear down child process trees. Monitor kills ship-pr wrapper bash but external agent grandchildren keep running after timeout. Document as accepted limitation or future process-group signaling (out of current scope).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

