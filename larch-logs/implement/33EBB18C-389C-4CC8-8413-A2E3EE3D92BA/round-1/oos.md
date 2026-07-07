### FINDING_2: [OUT_OF_SCOPE] Missing `.completed/step-3` still triggers the Step 5c refusal
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-pause-provenance
- **Severity**: minor
- **Concern**: Pausing in the Step 3 → Gate B window or resuming a legacy `STEP=5c` snapshot without `.completed/step-3` still hits the existing Step 5c provenance refusal. That behavior is pre-existing and outside this snapshot-copy fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-pause-provenance: Address the concern above.


Vote tally: YES=2 NO=0 JUDGE_ERROR=1 Result=accepted Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Pause-publish wiring is only indirectly asserted
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-pause-provenance
- **Severity**: minor
- **Concern**: Current tests only indirectly cover the pause-publish wiring, so a regression that drops the `pause` reason or `include_completed=true` on `_PublishDesignLogsRequest` could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Assert --reason pause in the publish argv or assert include_completed in the pause publish integration test.
  - From dyn-dyn-pause-provenance: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] `source-env.sh` is still omitted from pause snapshots
- **Reviewer(s)**: dyn-dyn-pause-provenance
- **Severity**: minor
- **Concern**: `source-env.sh` is still excluded from pause snapshots, so pause-load must reconstruct the session environment elsewhere; that is pre-existing and unrelated to the `.completed/` boundary fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-pause-provenance: Address the concern above.
Vote tally: YES=2 NO=0 JUDGE_ERROR=1 Result=accepted Fileable=false

