### FINDING_7: [OUT_OF_SCOPE] Duplicate COMBINED parse blocks may diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Identical `COMBINED_FALLBACK_COUNT` parse blocks exist in three design scripts. The reviewer marks this as intentional plan parity but notes future edits may diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider a shared parse helper in a follow-up if duplication grows.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_8: [OUT_OF_SCOPE] No-findings short-circuit omits dedup failure in DEGRADED_PANEL
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: In `skills/design/scripts/plan-review-loop.sh:532-536`, `_dedup_failed` does not contribute to `DEGRADED_PANEL` on the no-findings short-circuit, while the main path includes it. The reviewer marks this as pre-existing and not introduced by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_9: [OUT_OF_SCOPE] Decompose threshold is hardcoded
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/decompose-panel-dispatch.sh:208` hardcodes `floor_half=4` for an 8-slot panel. Future panel slot-count changes could desynchronize the degradation threshold from actual dispatch size.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Derive floor_half from manifest slot count like dispatch-plan-review-panel.sh.

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


