### FINDING_25: [OUT_OF_SCOPE] Clarify readers remain ad hoc
- **Reviewer(s)**: dyn-dyn-kv-wire
- **Severity**: major
- **Concern**: Plan-listed clarify publish/rename scans remain ad hoc and baselined, leaving duplicate and CR semantics split from the codec.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-kv-wire: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_26: [OUT_OF_SCOPE] Step 8 ship parsing bypasses the codec
- **Reviewer(s)**: dyn-dyn-kv-wire
- **Severity**: major
- **Concern**: Step 8 continues to use grep/tail/cut for ship-state reads, retaining a second parser surface outside the codec funnel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-kv-wire: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_27: [OUT_OF_SCOPE] Main-health sidecar remains ad hoc
- **Reviewer(s)**: dyn-dyn-kv-wire
- **Severity**: minor
- **Concern**: `_read_main_health_sidecar` still hand-parses environment rows and can diverge from shared codec duplicate and CR handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-kv-wire: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
