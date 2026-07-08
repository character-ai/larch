### [Plan Review] FINDING_2

### FINDING_2: Postmerge `TRANSIENT` should not share the global net-retry counter
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The first postmerge auto-rerun is still counted against the global `ship-pr-net-retries-python.count`, so runs that already spent earlier CI transients can stall instead of taking the intended postmerge repair handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: "In dispatch_ship.py exempt PHASE=postmerge-push-watch from ship-pr-net-retries-python.count or add a postmerge-specific reship path; add a test_implement_dispatch.py case with count=3 and postmerge TRANSIENT"


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/core/config.py
- **Concern**: [SCOPE-REDUCTION] Plan adds MAIN_HEALTH_MAX_TRANSIENT_RETRIES=1 while CI_MONITOR_TRANSIENT_RERUN_MAX is already 1 in the same module. Scenario: Two independent constants with the same bound can drift if one is tuned later; the diff adds config surface without new behavior
- **Proposed resolution**: Reuse config.CI_MONITOR_TRANSIENT_RERUN_MAX in _postmerge_main_health_gate (or assign MAIN_HEALTH_MAX_TRANSIENT_RETRIES = CI_MONITOR_TRANSIENT_RERUN_MAX) and drop the new constant from the plan unless a deliberate split is documented


