### FINDING_11: [OUT_OF_SCOPE] architecture: skills/review/scripts/test-review-core.sh:348
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Most run_core tests keep LARCH_AGGREGATOR_DISABLED=1 so review-core rarely hits real aggregate-findings dispatch. Limited integration coverage of collapsed aggregator inside review-core; pre-existing. Consider a review-core test without LARCH_AGGREGATOR_DISABLED using stub dispatch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] architecture: scripts/dispatch-with-waterfall.sh:275-278
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] cap_hit bypasses require-result-pattern by design. Documented accepted behavior: cap-hit without FINDING headings yields validation-failed not validation-exhausted. No change unless product policy changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] code-quality: (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated commits (#2878, tracking-issue-read, plugin version) mixed with #2881. Reviewers may miss or re-review unrelated surface area. Split PR or add a clear PR summary separating #2881 from drive-by fixes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_6: [OUT_OF_SCOPE] security: scripts/dispatch-with-waterfall.sh:275-278
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] cap_hit bypasses require-result-pattern. cap_hit artifacts without FINDING headings reach validation-failed instead of dispatcher fallback. Pre-existing; document or address in a follow-up if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

