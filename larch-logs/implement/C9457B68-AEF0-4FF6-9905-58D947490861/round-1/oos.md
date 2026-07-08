### OOS_1: [OUT_OF_SCOPE] Repair-loop docs still point at the retired launcher
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Repair-loop docs still reference the retired checks-commit-route launcher for step5-self-review, so stale direct-composite instructions can survive in the site table.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update repair-loop site table to run-step-checks.sh plus bgjob wait (sibling doc chunk).


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: [OUT_OF_SCOPE] Orphan-timeout tests still use the removed detach sidecar
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The orphan-timeout helper still depends on the removed `.step5-wrapper-detached` sidecar, so the bgjob-owned Step 5 path never exercises orphan-timeout stall emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Retire or rewrite orphan-timeout tests for bgjob ownership (pre-existing detach path).
  - From cursor-specialist-edge-cases: Remove or rewire orphan detection to bgjob registry in a follow-up
  - From cursor-specialist-testing: Update test to exercise bgjob-owned orphan path when wrapper contract is stable


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_3: [OUT_OF_SCOPE] Resume routing still mixes shell ownership with Python BGJOB_RC parsing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-bgjob-flow
- **Severity**: minor
- **Concern**: `checks_step5_resume_main` still leaves BGJOB_RC parsing unresolved at the Python boundary, so resume routing authority is split between shell and Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document shell ownership or add result-env BGJOB_RC relay if composite remains invoked directly.
  - From cursor-specialist-testing: Either add Python parsing if still required or update plan; shell path may be sufficient
  - From dyn-dyn-bgjob-flow: Document shell ownership or add result-env BGJOB_RC relay if composite remains invoked directly.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_4: [OUT_OF_SCOPE] Stale result-env behavior is still not regression-tested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The stale-env test only covers merge input, not the canonical result env, so the wait-layer stale-DONE race is not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Assert deletion or ignore of bgjob/implement-step5-review.result.env on fresh start


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_5: [OUT_OF_SCOPE] Anti-polling pins still target Step 5 terminal probes
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The anti-polling harness still pins terminal probes for Step 5, so its checks can drift from the bgjob contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update pins in the anti-polling harness chunk
  - From cursor-specialist-testing: Update Step 5 rows when that MAY_UPDATE harness is touched


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_6: [OUT_OF_SCOPE] Resume launcher can still duplicate an in-flight Step 5 review
- **Reviewer(s)**: dyn-dyn-bgjob-flow
- **Severity**: major
- **Concern**: Unlike `step-5-review.sh`, the resume launcher has no live-registry rejoin guard before `bgjob start`, so a repeated MAV/coder resume invocation can start a second daemon racing on the same merge/result envs.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_7: [OUT_OF_SCOPE] Structure pins still cover legacy stall seeding but not the new rejoin contract
- **Reviewer(s)**: dyn-dyn-bgjob-flow
- **Severity**: minor
- **Concern**: The structure pins still cover legacy stall seeding on `step5-review-branches.md` but do not require the new “Bgjob rejoin and resume contract” text or explicit BGJOB_RC=0 gating for the review loop, so prose regressions there would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

