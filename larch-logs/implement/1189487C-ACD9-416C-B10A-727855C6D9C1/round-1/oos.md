### OOS_1: [OUT_OF_SCOPE] Step 7a bgjob start omits explicit owner PID
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: Step 7a's bgjob launcher does not pass an explicit owner PID the way the Bash launchers do. That makes start behavior and orphan detection depend on environment fallback, which can fail or become weaker when the env var is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-contract: Address the concern above.


Vote tally: YES=0 NO=1 JUDGE_ERROR=2 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] wait fences omit required timeout 330000
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: The Step 3/6/7a wait fences do not repeat `bgjob-wait.md`'s required Bash tool timeout annotation. Long waits can hit the default tool timeout before the daemon finishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-contract: Address the concern above.


Vote tally: YES=0 NO=1 JUDGE_ERROR=2 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] stale hook semantics still treat old Step 3 checks as bg-wait
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The legacy hook still treats `implement-step3-checks` as bg-wait even though the migrated wrappers no longer write markers. Resume paths may hit stale hook semantics until the planned cleanup retires those rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=1 JUDGE_ERROR=2 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] abandoned-checks classification still depends on .bg-wait-active
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Abandoned-checks stall classification still depends on `.bg-wait-active`, which the migrated legs no longer maintain. Externally killed checks can misclassify until the stall/state migration lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=1 JUDGE_ERROR=2 Result=rejected Fileable=false

### OOS_5: [OUT_OF_SCOPE] rebase probe still reports NEXT_ACTION=continue on conflict
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: The `4.r` rebase probe still emits `NEXT_ACTION=continue` on non-zero exit. That preexisting ambiguity becomes more visible now that BGJOB_RC gating can block the routable conflict path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-bgjob-contract: Address the concern above.


Vote tally: YES=0 NO=1 JUDGE_ERROR=2 Result=rejected Fileable=false

### OOS_6: [OUT_OF_SCOPE] structure harness does not pin BGJOB_RC=0 in SKILL prose
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The structure harness does not pin `BGJOB_RC=0` in the Step 3/6/7a SKILL prose, so future removal of the gate could slip past CI while the checks-repair-loop pin stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=1 JUDGE_ERROR=2 Result=rejected Fileable=false

