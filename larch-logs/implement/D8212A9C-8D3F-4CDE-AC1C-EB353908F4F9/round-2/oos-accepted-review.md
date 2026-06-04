### FINDING_19: [OUT_OF_SCOPE] architecture: skills/design/SKILL.md:1027-1041
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Sentinel suppresses preview on every Step 3 re-entry without checking whether plan.txt was repaired after an earlier missing-plan warning. Operator fixes plan.txt then triggers Gate C re-run; preview fence exits quietly; review runs with no refreshed ## Plan Candidate for Review and no repeated warning. Consider future enhancement: tie re-entry suppression to plan.txt presence/mtime, or clear sentinel when plan.txt becomes non-empty.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_20: [OUT_OF_SCOPE] risk-integration: skills/design/SKILL.md:1029-1074
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Uncaptured preview and captured review read plan.txt at different times if the tree mutates between fences. Operator sees preview from revision N while plan-review-loop reviews revision N+1; confusing triage of review findings vs chat preview. Document for operators; optional follow-up to invalidate sentinel or re-preview on plan.txt change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_21: [OUT_OF_SCOPE] correctness: skills/design/scripts/run-step3-review.sh:86-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Preview-mode canonicalization uses bare cd under set -e. Rare cd failure after validate passes aborts the whole Step 3 preview Bash block instead of degrading with a warning. Wrap cd in set +e; on failure skip sentinel touch and still run renderer on raw --design-tmpdir.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


