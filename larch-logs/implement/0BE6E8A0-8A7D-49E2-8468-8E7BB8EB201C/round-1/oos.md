### FINDING_6: [OUT_OF_SCOPE] daemon launch semantics may differ from the plan
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The current launch shape may not match the planned double-fork/session semantics, so behavior could differ from the migration contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document or add second fork per plan


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] follow-up migration work is still outside this diff
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Some launch-site migration work and follow-up harness work are not in this diff, so the branch alone cannot satisfy the full acceptance set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Land follow-up migration PRs
  - From cursor-specialist-testing: Out of scope for this diff; add in follow-up


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] stale registry rows still need a recovery path
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: A dead registry can still block background launches until a later reap pass, leaving a manual recovery gap for operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document mid-session bgjob reap for operators


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] abandoned checks still use the old bg-wait marker
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: State code still keys abandoned checks off the old marker rather than the bgjob registry, so migration can misclassify stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Pre-existing; update with wrapper migration


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] skill docs still teach `run_in_background`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Skill docs still instruct the legacy `run_in_background` path, so operator guidance is not yet aligned with the new contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Allowlisted interim state per plan


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_17: [OUT_OF_SCOPE] legacy hook compatibility metadata is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Compatibility hooks and allowlist metadata are not yet fully aligned with the planned bgjob wait loops, so future migration edits can hit missing harness support or allowlist drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Update both hooks when enabling bgjob wait loops.
  - From cursor-specialist-testing: Add the seeded allowlist row with reason comment.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_18: [OUT_OF_SCOPE] the deny hook still has a pre-registry startup window
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-bgjob-lifecycle
- **Severity**: minor
- **Concern**: The deny hook still leaves a pre-registry startup window where background launches are not blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Accept as transitional or broaden active-run detection once migration starts.
  - From dyn-dyn-bgjob-lifecycle: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_21: [OUT_OF_SCOPE] sentinel writes remain non-atomic and silent
- **Reviewer(s)**: dyn-dyn-bgjob-lifecycle
- **Severity**: minor
- **Concern**: Sentinel writes remain non-atomic and silently suppress failures, so compatibility markers can disappear without notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-lifecycle: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_22: [OUT_OF_SCOPE] bgjob test coverage is still missing
- **Reviewer(s)**: dyn-dyn-bgjob-lifecycle
- **Severity**: minor
- **Concern**: The current pytest surface does not cover the migration's orphan/reap/start-wait edge cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-lifecycle: Address the concern above.
Vote tally: YES=1 NO=1 JUDGE_ERROR=1 Result=neutral Fileable=false

