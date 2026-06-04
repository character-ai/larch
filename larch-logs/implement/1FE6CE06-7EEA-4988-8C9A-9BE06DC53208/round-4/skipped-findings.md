### FINDING_26: architecture: skills/design/scripts/plan-review-loop.sh:835-883
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan scoped changes to design-log publish/merge files only; branch also modifies plan-review collector stderr and multi-round integration quiet-mode handling. A #3413-focused reviewer or rollback of publish changes could miss unrelated plan-review behavior changes; violates plan Approach to keep the fix local to the flush path. Remove these hunks from this PR or update the plan/acceptance to explicitly include them with rationale.
- **Suggested revision**: Address the concern above.



