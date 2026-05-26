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

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/dispatch-with-waterfall.sh:275-278` — `STATUS=cap_hit` still bypasses `--require-result-pattern`, so a cap-hit artifact without structured headings can reach the post-dispatch validator and exit as `validation-failed` rather than triggering dispatcher fallback. Pre-existing (#2895); documented as accepted; not introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** Session tmpdir trust model — `aggregator-dispatch.env`, `ALL_OUTPUT_FILES_PATH` sidecars, and `aggregate-validate.py` under `$REVIEW_TMPDIR` remain tamperable by anything with write access to the session directory (consistent with `SECURITY.md` retry-metadata posture). Candidate **content** is still gated by the python validator; this PR adds candidate **path** pinning, which is stricter than `decompose-aggregator.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `skills/review/scripts/aggregate-findings.sh:712-714` — `ALL_OUTPUT_FILES_PATH` itself is not required to resolve under `$REVIEW_TMPDIR` before `read -r cand` (same pattern as `decompose-aggregator.sh`). Only the resolved `cand` path is canonicalized. Impact is limited to first-line reads from attacker-chosen sidecar locations when `aggregator-dispatch.env` is tampered; merge content still cannot replace `findings.md` without passing validation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/review/scripts/aggregate-findings.sh:99
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] count_finding_blocks looser than validator heading contract Pre-existing pseudo-heading edge if gate bypassed Align grep with validator when touching heading rules
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/review/scripts/test-aggregate-findings.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness doc omits new dispatcher integration coverage Contributors may not discover phase-2 fallback tests Add short section listing dispatcher-layer cases
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

