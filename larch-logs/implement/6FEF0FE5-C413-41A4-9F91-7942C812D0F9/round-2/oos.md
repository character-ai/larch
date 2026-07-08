### OOS_1: Stall-recovery prose still mentions legacy Step 8 relaunch
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Stall-recovery still documents the retired Step 8 background relaunch flow, while the stall/state chunk owns the migration off the old notification contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Hook poll-guard still references retired bg-wait markers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Hook poll-guard still refers to legacy Step 8 bg-wait markers after the wrapper stopped writing `.bg-wait-active`, and the marker cleanup belongs in the hook cleanup chunk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: dispatch_ship sidecar-first behavior remains intentional
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: route-exit only validates the bgjob result env when the file exists, but that matches the documented sidecar-first behavior and the rejected fail-closed change, so this chunk does not need a code change unless policy is reopened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

