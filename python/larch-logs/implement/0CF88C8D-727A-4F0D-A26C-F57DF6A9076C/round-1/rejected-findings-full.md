### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: (plan — acceptance / testing strategy)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No end-to-end test proves normalized accepted OOS reaches `/issue` filing parsers. Counters and disposition gates can pass while Step 9a.1 still cannot file blocks if parser/schema wiring regresses. Add harness: normalized oos-accepted-review.md → parse-input.sh OOS mode → assert parsed/filed OOS item.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: risk-integration: skills/review/scripts/emit-tally.sh:671-685
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] emit-tally preserve skips oos-serialize.sh whenever OOS_ACCEPTED_COUNT>0, so scope-drift bare FINDING blocks bypass serialize's secondary security tag scan. Scope-drift OOS about sensitive out-of-plan paths without a detectable security marker is normalized and preserved for public filing without the serialize fallback filter. Apply shared security classification immediately before normalize-oos-block-header.sh in tally and review-and-fix, matching oos-serialize semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/review/scripts/tally-code-votes.sh:122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NORMALIZE_OOS_HELPER uses SCRIPT_DIR-relative path while PLUGIN_ROOT is already available. Helper resolution is inconsistent with review-and-fix.sh and breaks if script layout changes. Use $PLUGIN_ROOT/skills/shared/scripts/normalize-oos-block-header.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1456-1478
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Skipped-OOS branch invokes is_security_block twice per non-security block. Redundant classifier subprocess calls on every SKIPPED append add noise and maintenance cost. Normalize directly in the else branch without re-invoking is_security_block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

