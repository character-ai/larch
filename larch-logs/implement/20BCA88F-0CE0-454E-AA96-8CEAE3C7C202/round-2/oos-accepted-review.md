### FINDING_13: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:2760-2762
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Post-rebump gh pr edit uses with_transient_retry with outer || true and never reads _WTR_RC Persistent title sync failure is silent (best-effort by design) Optional: read _WTR_RC and log at debug level without failing ship-pr
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_14: [OUT_OF_SCOPE] correctness: scripts/design-log-publish.sh:685-686
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Remote branch cleanup skipped when gh pr list probe fails (recovery_probe_ok=false) All create retries fail and list probe fails; orphan remote branch remains and operator retry can NFF on push Document operator recovery or retry list with separate cleanup policy
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


