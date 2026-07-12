### OOS_1: [OUT_OF_SCOPE] Reconciliation finalize writes bypass the normal helper
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Reconciliation uses `_write_terminal_layer` for finalize state rather than the standard finalize-state helper, which may omit fields used by the normal post-merge path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] Reconciliation does not validate the run branch or PR head
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-recovery-state
- **Severity**: minor
- **Concern**: An operator can nominate a merged PR from the repository without proving that its branch or head belongs to the run being recovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-recovery-state: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_3: [OUT_OF_SCOPE] End-to-end waiver resume coverage is absent
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The plan-requested integration coverage for operator-bail followed by waiver resume and preserved attempt counters is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] Anti-halt harness does not pin operator choices
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Exact `AskUserQuestion` option strings for proceeding without assessment and stopping are not asserted by the anti-halt harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_5: [OUT_OF_SCOPE] Reconciliation lacks symlink refusal tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Symlinked state-layer files are not tested to ensure manual recovery fails closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_6: [OUT_OF_SCOPE] Historical run-log repair lacks scanner coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No automated fixture validates repaired historical run-log artifacts against existing scanners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_7: [OUT_OF_SCOPE] Reconciliation cannot clear orchestrator memory
- **Reviewer(s)**: dyn-dyn-recovery-state
- **Severity**: minor
- **Concern**: Reconciliation clears persisted stall fields but cannot clear an orchestrator’s in-memory or ambient `STALL_TRACKING` value; the caller must pass the documented cleared flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-recovery-state: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
