### FINDING_11: [OUT_OF_SCOPE] Repair-loop documentation conflicts with implemented exhaustion routing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Documentation still describes exhausted pre-ship paths as `main-agent-edit` while the implemented contract routes named exhaustion to `stall`. This can cause orchestration prose to reintroduce inline editing after ordinary waterfall exhaustion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Align section 3 exhausted prose with section 4 stall remapping.
  - From cursor-specialist-edge-cases: Remove or rewrite the exhausted+ledger main-agent-edit paragraph; limit main-agent-edit to explicit structural main-agent-required outcomes.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Test expectations are stale relative to the updated structural and pre-ship stall contracts
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: Several tests still encode retired behavior: a hard-coded 300-second timeout, generic structural `dispatch-failed`, pre-ship exhaustion escalation tokens, and a failed status for the unchanged ship-pr internal handoff. These expectations can either fail against the new contract or pass for the wrong reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Assert config.FIXER_LANE_TIMEOUT_SEC in launcher argv builders.
  - From cursor-specialist-correctness: Expect main-agent-edit for structural dispatch-failed once code is fixed.
  - From cursor-specialist-testing: Fix the test to assert main-agent-required and ship-pr ledger tokens.
  - From dyn-dyn-waterfall-state: The production routing matches round-1 intent; only the test expectation is stale.
  - From dyn-dyn-waterfall-state: That aligns with the new pre-ship stall contract; the test name and assertions predate the remapping.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Documentation does not explain which stall paths require named lint-fix evidence
- **Reviewer(s)**: dyn-dyn-waterfall-state
- **Severity**: minor
- **Concern**: Operators may interpret missing `FAILURE_REASON` on `no-changes-stale` or generic repair-loop `exhausted` as a routing defect, although only the three closed lint-fix reasons require `FAILURE_REASON` and `LINT_FIX_TIER_LEDGER_PATH`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-waterfall-state: Consider documenting that only the three closed lint-fix reasons require `FAILURE_REASON` + `LINT_FIX_TIER_LEDGER_PATH`, so operators do not treat missing `FAILURE_REASON` on `LOOP_STATUS=no-changes-stale` as a routing bug.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
