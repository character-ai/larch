### OOS_1: Timeout argv expectations are stale
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: major
- **Concern**: Tests still expect a 300-second timeout even though the implementation uses `FIXER_LANE_TIMEOUT_SEC`, currently 1800 seconds. The test contract and launcher coverage need to match the configured timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update test to expect 1800.
  - From cursor-specialist-testing: Assert `str(config.FIXER_LANE_TIMEOUT_SEC)` for all three external launch argv builders; add Claude launcher coverage.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: Ship-pr exhaustion tests assert obsolete routing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: Ship-pr tests expect pre-ship failed or stall semantics and stale ledger fields, while the current ship-pr exhaustion contract preserves `main-agent-required` for `ship-pr-ci-*` sites. The tests should reflect the production handoff semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Expect `main-agent-required` for ship-pr-ci-initial no-tool exhaustion.
  - From cursor-specialist-testing: Restore ship-pr `main-agent-required` assertions and add dedicated ship-pr exhaustion regression tests per plan.
  - From dyn-dyn-waterfall-state: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_3: Repair-loop reference documentation is stale
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-waterfall-state
- **Severity**: minor
- **Concern**: The repair-loop reference still documents inline main-agent repair for exhausted runs with a ledger, conflicting with the current pre-ship stall rule and structural-only main-agent-edit routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Rewrite section 4 to document stall-only pre-ship exhaustion and structural-only main-agent-edit.
  - From dyn-dyn-waterfall-state: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_4: Plan-required targeted tests are missing
- **Reviewer(s)**: dyn-dyn-waterfall-state
- **Severity**: minor
- **Concern**: The updated test module lacks targeted coverage for lane-budget reservation, final-tier eligibility after full-lane attempts, exit-zero no-op advancement, and execution-issue emission beyond limited repair-loop unit coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-waterfall-state: Address the concern above.
Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false
