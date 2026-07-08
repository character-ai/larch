### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/core/config.py
- **Concern**: [SCOPE-REDUCTION] Plan adds MAIN_HEALTH_MAX_TRANSIENT_RETRIES=1 while CI_MONITOR_TRANSIENT_RERUN_MAX is already 1 in the same module. Scenario: Two independent constants with the same bound can drift if one is tuned later; the diff adds config surface without new behavior
- **Proposed resolution**: Reuse config.CI_MONITOR_TRANSIENT_RERUN_MAX in _postmerge_main_health_gate (or assign MAIN_HEALTH_MAX_TRANSIENT_RETRIES = CI_MONITOR_TRANSIENT_RERUN_MAX) and drop the new constant from the plan unless a deliberate split is documented

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship.py:747-780; skills/implement/references/ship-pr-exit-matrix.md:23,43
- **Concern**: [SCOPE-REDUCTION] Postmerge rerun is routed through the generic rc 6 reship path. Scenario: After the PR is already merged, the planned failed-run rerun returns Outcome.TRANSIENT. route-exit maps rc 6 to reship, and reship runs ship pre-fix-rebase for every non-phase14 reship. That can rebase or conflict on the original merged feature branch before the driver can re-check the now-green main run, so the recovery path can still dead-end.
- **Proposed resolution**: Keep the narrow emergency-repair relaunch re-verification fix and drop the automatic postmerge rerun, or add an explicit postmerge-push-watch closed-PR reship carve-out that skips pre-fix rebase and relaunches the driver only.
