### OOS_6: Multi-round integration harness remains single-pass ([OUT_OF_SCOPE] source included)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-workflow-contracts-output.txt
- **Severity**: important
- **Concern**: The named multi-round integration test still only verifies a single review pass and does not exercise Gate B → continuation → second review behavior, cumulative artifacts, counters, or terminal statuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-workflow-contracts-output.txt: Address the concern above.


### OOS_7: Cumulative accepted-all restore/append behavior lacks behavioral tests ([OUT_OF_SCOPE] source included)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-artifact-accounting-output.txt
- **Severity**: important
- **Concern**: The new `accepted-plan-findings-all.md` accumulation, restore, append, and manual-reset semantics are not covered by behavioral tests, leaving stale or missing cumulative findings possible after failures or sequential rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-artifact-accounting-output.txt: Address the concern above.


### OOS_8: [OUT_OF_SCOPE] Design loop lacks churn warning analogous to `/implement`
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: nit
- **Concern**: `/design` automatic continuation has no operator-visible churn signal when later rounds accept more findings than earlier rounds, unlike `/implement` Step 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.


### OOS_9: [OUT_OF_SCOPE] Linting docs still describe old tiered cap behavior
- **Reviewer(s)**: dyn-workflow-contracts-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` still says the Step 3 review cap test covers HARD-tier blocking on the sixth entry even though the cap is now flattened to 5 for both tiers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-contracts-output.txt: Address the concern above.


### OOS_10: [OUT_OF_SCOPE] Approval-gates binding convention still references per-tier cap behavior
- **Reviewer(s)**: dyn-workflow-contracts-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md` still references “per-tier behavior” for review-round caps even though cap prose was flattened elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-contracts-output.txt: Address the concern above.

### OOS_11: Single-important accepted finding triggers continuation despite `/implement` threshold ([OUT_OF_SCOPE] source included)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-artifact-accounting-output.txt, dyn-workflow-contracts-output.txt
- **Severity**: important
- **Concern**: The design continuation helper treats `HIGH_ACCEPTED_COUNT > 0` as substantial, while `/implement` uses `high_n >= 2` unless other structural/fix-count signals apply. This can force extra design review rounds for a single important finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-artifact-accounting-output.txt, dyn-workflow-contracts-output.txt: Address the concern above.


