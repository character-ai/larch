### FINDING_19: correctness: skills/design/scripts/tally-plan-review.sh:132-177
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --voter slot assignment uses basename/tool heuristics not argv order. Direct --voter Cursor then Claude invocations mis-order v1/v3 relative to dispatch order documentation. Assign vN by --voter enumeration index in --voter mode; reserve heuristics for --voter-files only.
- **Suggested revision**: Address the concern above.



### FINDING_3: code-quality: skills/design/scripts/tally-plan-review.sh:132-197
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] --voter slot assignment uses position_for_voter heuristics not argv order Direct tally with non-canonical path order mis-assigns vN columns vs plan dispatch-order wording For --voter mode use explicit slot index; reserve heuristics for --voter-files only
- **Suggested revision**: Address the concern above.



### FINDING_7: correctness: skills/design/scripts/tally-plan-review.sh:132-197
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] --voter slot assignment uses basename/tool heuristics not argv dispatch order per plan. Custom --voter paths without slot markers can land in wrong vN columns or hit duplicate position errors despite canonical dispatch order from plan-review-loop. Assign v1/v2/v3 by --voter argument order; reserve position_for_voter for legacy --voter-files only.
- **Suggested revision**: Address the concern above.



### FINDING_9: correctness: skills/design/scripts/tally-plan-review.sh:79-81
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Argv contract errors exit 2; plan specifies exit 1. Callers grepping for exit 1 on mutex/invalid slot miss failures. Align exit code with plan and test-tally-plan-review.sh or update contract docs.
- **Suggested revision**: Address the concern above.



