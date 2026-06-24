### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:147
- **Concern**: [SCOPE-REDUCTION] Edge-case bullet mislabels empty coder as a _step2_blockers case. Scenario: Step 2 blockers in code are only REPO_UNAVAILABLE, PLAN_FILE, and missing tmpdir plan.txt / feature-description.txt (python/bootstrap.py:1112-1122). Empty coder is gated by _continue_predicate (python/bootstrap.py:1338-1345), which sets continue_tail_attempted=false without touching _step2_blockers. Listing empty coder under step2-blocker cases contradicts plan.txt:38 (reuse _step2_blockers; do not re-encode inline) and can push implementers to extend _step2_blockers for empty coder.
- **Proposed resolution**: Revise the edge-case bullet: empty coder routes to cleanup via continue_tail_attempted=false and the step2 branch guard (non-empty coder), not via _step2_blockers. Keep _step2_blockers limited to repo/plan artifact checks.
