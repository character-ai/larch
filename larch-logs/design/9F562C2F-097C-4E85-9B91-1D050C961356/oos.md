### FINDING_1: Emergency-repair resume can re-check a green rerun with the wrong flap setting
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The emergency-repair relaunch path confirms the merged SHA is green with `skip_flap_check=True`, but then `run_postmerge_phase()` can re-enter the main-health gate with the default flap check and reclassify the same cleared run as a failure instead of finalizing merged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Thread the recovery bypass into `run_postmerge_phase()` and `_postmerge_main_health_gate()` for this resume path, or finalize directly after the green pre-check succeeds"


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Postmerge retry state should not reuse ship-wide `TRANSIENT_RETRIES`
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-Ship Ci State Machine
- **Severity**: major
- **Concern**: The postmerge flap guard and retry budget are both being derived from the same ship-wide `TRANSIENT_RETRIES` history, so unrelated CI transients can either suppress same-SHA flap detection or consume the postmerge retry budget before the first genuine postmerge rerun.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: "Use a postmerge-specific retry marker, or gate the bypass only on the explicit postmerge retry path that just submitted `rerun_failed()`."
  - From Cursor-Pragmatic: "Add a postmerge-only counter (for example MAIN_HEALTH_TRANSIENT_RETRIES in ship_state.py/ship_seed.py, optional ShipReconciliationCounters field) incremented only when _postmerge_main_health_gate submits a main-health rerun; gate skip_flap_check and MAIN_HEALTH_MAX_TRANSIENT_RETRIES on that counter only. Add a test_ship.py case that seeds TRANSIENT_RETRIES=1 from a prior CI transient and asserts the first postmerge failure still calls rerun_failed once and returns Outcome.TRANSIENT."
  - From Codex-Requirements: "Use a postmerge-specific persisted retry marker or counter for both skip_flap_check and the postmerge rerun budget, or reset/translate the counter at postmerge entry so only a submitted postmerge rerun enables skip_flap_check."
  - From Cursor-dyn-Ship Ci State Machine: "Use a postmerge-only counter (for example POSTMERGE_MAIN_HEALTH_TRANSIENT_RETRIES) or gate the rerun on increments written only from _postmerge_main_health_gate, not on the CI-monitor shared TRANSIENT_RETRIES field."


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: Postmerge behavior change needs the first-failure test rewritten
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The existing postmerge test still encodes the old immediate `NEEDS_USER_INPUT` behavior, so it will fail once the first failure becomes a transient retry and the new path will be harder to verify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: "Rewrite this case into a first-failure transient assertion plus a separate second-failure emergency-repair assertion."


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: Emergency-repair resume needs an explicit empty-branch guard
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The resume flow can jump from emergency-repair back into main-health polling without making the empty `EMERGENCY_REPAIR_BRANCH` check an explicit gate, which risks finalizing a run while a real repair branch or PR is still active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: "In the run_ship resume.start == \"emergency-repair\" steps, make the empty EMERGENCY_REPAIR_BRANCH (and no repair PR) check an explicit ordered guard before read_main_health/run_postmerge_phase; add a test_ship.py case with EMERGENCY_REPAIR_BRANCH set that asserts no run_postmerge_phase call and NEEDS_USER_INPUT is preserved."


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_6: Postmerge reship can re-enter emergency-repair before the rerun settles
- **Reviewer(s)**: Cursor-dyn-Ship Ci State Machine
- **Severity**: major
- **Concern**: The driver returns `TRANSIENT` as soon as the rerun is submitted, but the next pass can still observe the old failed run before the rerun reaches a settled terminal state, so the gate can spend the budget and write `PHASE=emergency-repair` while the auto-rerun is still in flight.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Ship Ci State Machine: "Persist the failed run id when emitting TRANSIENT (plan already says preserve failed-run context but only names PHASE/TRANSIENT_RETRIES). On re-entry with TRANSIENT_RETRIES>0, treat fail on that same run id as pending: poll until it reaches success, a different terminal failure, or MAIN_HEALTH_WAIT_TIMEOUT_SEC, then only spend the emergency-repair budget on a confirmed failure. Mirror the post-rerun settle loop in python/larch/design/design_log_ship.py:223-228."


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship.py:747-780; skills/implement/references/ship-pr-exit-matrix.md:23,43
- **Concern**: [SCOPE-REDUCTION] Postmerge rerun is routed through the generic rc 6 reship path. Scenario: After the PR is already merged, the planned failed-run rerun returns Outcome.TRANSIENT. route-exit maps rc 6 to reship, and reship runs ship pre-fix-rebase for every non-phase14 reship. That can rebase or conflict on the original merged feature branch before the driver can re-check the now-green main run, so the recovery path can still dead-end.
- **Proposed resolution**: Keep the narrow emergency-repair relaunch re-verification fix and drop the automatic postmerge rerun, or add an explicit postmerge-push-watch closed-PR reship carve-out that skips pre-fix rebase and relaunches the driver only.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Add MAIN_HEALTH_MAX_TRANSIENT_RETRIES duplicates existing CI_MONITOR_TRANSIENT_RERUN_MAX=1
- **Description**: Add MAIN_HEALTH_MAX_TRANSIENT_RETRIES duplicates existing CI_MONITOR_TRANSIENT_RERUN_MAX=1. Scenario: A second constant with the same bound can drift from CI_MONITOR_TRANSIENT_RERUN_MAX without behavioral benefit for this narrow fix.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/core/config.py:687
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

