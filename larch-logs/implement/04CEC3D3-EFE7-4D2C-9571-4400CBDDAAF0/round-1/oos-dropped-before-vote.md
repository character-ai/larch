### OOS_1: [OUT_OF_SCOPE] `python/larch/review/plan_review_common.py` unreachable round-three authorization branch
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-cap-policy
- **Severity**: latent
- **Concern**: The `ROUND_THREE_AUTHORIZATION_CAP` bonus branch in `effective_authorized_cap` is unreachable under the current universal cap of 2, so it is dead code that can mislead future cap changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Simplify or remove ROUND_THREE_AUTHORIZATION_CAP branch in a cleanup PR
  - From cursor-specialist-testing: Merge into tier_ceiling-only path or delete dead branch in follow-up
  - From dyn-dyn-cap-policy: Remove or rewrite the bonus branch now that all tiers share cap 2.

### OOS_2: [OUT_OF_SCOPE] plan update omits the convergence-guard rationale
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The convergence-guard change is not reflected in the plan UPDATED list, leaving a traceability gap for reviewers and operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Document in plan or commit message rationale

