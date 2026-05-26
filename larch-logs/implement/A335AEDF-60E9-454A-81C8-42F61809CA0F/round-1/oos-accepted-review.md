### FINDING_11: [OUT_OF_SCOPE] architecture: skills/review/scripts/aggregate-findings.sh:536-567
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan claims attestation-only duplicate merge yields REASON=ok but validator always RC=1 for attestation + zero blocks + nonempty input. Pre-existing semantic/doc mismatch not introduced by this diff. Address separately if duplicate-only attestation should succeed validation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/review-core.md:91
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Breadcrumb doc predicate (LARCH_QUIET_BREADCRUMBS) does not match unconditional emit_breadcrumb call site. Operators may misconfigure breadcrumb expectations. Align review-core.md with lib-quiet gating (pre-existing).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_17: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/test-review-core.sh:446-458
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] aggregator-validation-exhausted test uses aggregate stub not real aggregate-findings narrow-trigger path. Regression in aggregate-findings REASON mapping might not break review-core harness. Add end-to-end case wiring real aggregate stub output (pre-existing gap).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


