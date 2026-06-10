### OOS_1: [OUT_OF_SCOPE] Legacy bash merge path still lacks REVIEW_REQUIRED handling
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The Python merge driver gained `REVIEW_REQUIRED` handling, but the legacy `scripts/merge-pr.sh` path remains unchanged. Operators using `LARCH_SHIP_PR_IMPL=bash` may still hit iteration-cap stalls on review-blocked PRs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document bash opt-in gap or port reviewDecision handling to merge-pr.sh in a follow-up


