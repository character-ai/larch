### FINDING_2: Route-exit can proceed without a result env
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-auto, dyn-dyn-bgjob-handoff
- **Severity**: major
- **Concern**: `_ship_route_bgjob_result_error()` does not fail when `implement-step8-ship.result.env` is missing, so route-exit can trust sidecars alone and emit `NEXT_ACTION=*` from stale or incomplete evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Require readable result env for implement-step8-ship before route-exit; fail closed when missing or wrong STEP.
  - From cursor-specialist-plan-fidelity-auto: Fail closed when the Step 8 result env is missing or lacks STEP=implement-step8-ship after bgjob migration.
  - From dyn-dyn-bgjob-handoff: When handoff sidecars are present, require a readable result env for route-exit and fail closed with a explicit error if it is missing, symlinked, or non-regular; keep the current rc/json cross-checks when the file exists.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: [OUT_OF_SCOPE] Stall-recovery docs still reference legacy Step 8 relaunch prose
- **Reviewer(s)**: cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: The stall-recovery reference still describes the old Step 8 background relaunch flow, but that migration belongs in the stall/state sibling chunk rather than this one.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Migrate in the stall/state chunk per #6524 plan.
  - From cursor-specialist-plan-fidelity-auto: Track in the stall/state chunk issue; no change required here.


Vote tally: YES=1 NO=1 JUDGE_ERROR=1 Result=neutral Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Plan file naming looks stale
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: The plan mentions `implement_dispatch.py` while the diff touches `dispatch_ship.py`, which suggests the plan/file mapping may be stale rather than a behavioral issue in the chunk itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Update plan provenance or add a no-op comment only if maintainers want file-list parity.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Wrapper harness omits the planned terminal-failure relaunch pins
- **Reviewer(s)**: dyn-dyn-bgjob-handoff
- **Severity**: major
- **Concern**: The rewritten wrapper harness stays at launcher/child/rejoin static contracts and leaves the dynamic terminal-failure relaunch pins to the route-exit layer, which misses the layer where the relaunch bug actually lives; that coverage belongs with the sibling chunk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-handoff: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Hook poll-guard alignment is stale
- **Reviewer(s)**: dyn-dyn-bgjob-handoff
- **Severity**: minor
- **Concern**: The hook still keys live waits off `.bg-wait-active` even though migrated Step 8 paths no longer write it, which is a follow-on hook alignment cleanup rather than a regression in the new wrapper logic itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-handoff: Address the concern above.
Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

