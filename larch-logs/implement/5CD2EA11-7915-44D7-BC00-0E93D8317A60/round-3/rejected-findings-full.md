### [rejected] FINDING_13

### FINDING_13: code-quality: scripts/test-larch-log.sh:3156-3192
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale-run test duplicates plan-goals heredoc instead of reusing existing payload helper per plan. Two tests can drift if plan-goals validity rules tighten. Reuse shared payload file or tiny generator function.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_14

### FINDING_14: correctness: docs/run-logs.md (manifest.json section per branch diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Shipped manifest status prose contradicts implementation_plan §3 (qualified vs always in-progress). A reviewer treating the plan as normative flags a doc defect even though the new text matches tests that commit status=done. Align plan checklist and shipped doc to a single agreed contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_16

### FINDING_16: correctness: scripts/ship-pr.sh:2809-2865
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] rewrite_reasoning_new_version always appends Rebase + Re-bump Correction on each successful replace Repeated correction could duplicate audit sections Make rewrite idempotent or detect existing correction block
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: correctness: scripts/ship-pr.sh:2967-2972
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Regression correction case *) keeps _corrected at stale new_version for unknown bump_type. Unexpected BUMP_TYPE with regression detected skips auto-correction until apply-bump fails. Normalize or reject unknown bump_type on the correction path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: correctness: scripts/ship-pr.sh:2976-3024
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] If reasoning rewrite and fallback both fail, version-bump-reasoning larch-log write is skipped while apply-bump may succeed. Landed version correct in git but committed run log lacks refreshed reasoning batch. Fail closed on correction without publishable reasoning, or emit minimal stub without awk shape dependency.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_19

### FINDING_19: correctness: scripts/test-larch-log.sh (stale-run isolation test per branch diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New stale-run test uses a bespoke payload instead of reusing $_spayload as the plan specified. Future edits to $_spayload could drift from the duplicated heredoc without failing until someone audits test fidelity. Reuse $_spayload or document structural coupling to $_spayload.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_20

### FINDING_20: correctness: scripts/test-larch-log.sh:195-224
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Regression test uses a new $_stale_payload heredoc instead of reusing the plan-named payload variable. Minor plan-fidelity and DRY drift; behavior of the test is still coherent. Reuse an in-scope payload path (e.g. $_cpayload) or adjust the plan's variable name to match the file.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_21

### FINDING_21: risk-integration: docs/run-logs.md:73
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Committed manifest status prose diverges from the implementation plan's simpler always-in-progress blockquote. Stakeholder signs off against the literal plan text and marks the doc bullet undelivered even though the shipped wording is more accurate. Reconcile the written plan or PR checklist with the nuanced paragraph, or revert to the plan wording only if that invariant is truly intended.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_7

### FINDING_7: architecture: scripts/larch-log.sh:430-432
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Commit-pathspec inline comment omits the symlink-resolution rationale from Implementation Plan 1. Only documentation drift; scripts/larch-log.md still explains symlinks. Align the shell comment with scripts/larch-log.md:76-79 or the plan's stated motivation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: architecture: scripts/ship-pr.sh:2797-2807,.claude/skills/bump-version/scripts/apply-bump.sh:41-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate semver_lt implementations added in two scripts. Future semver edge-case fixes might update only one copy. Extract shared helper or add explicit sync comments.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: code-quality: plan
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] docs/run-logs.md:378-383 Manifest status doc diverges from plan absolutist wording by allowing exceptions. Plan checklist may show false gap if read literally. Reconcile plan text with doc or accept as intentional accuracy improvement.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

