---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Emergency-repair skip should be terminal
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The emergency-repair transient recovery path still requires `health.status == pass`, so a legitimate `skip` result can leave a resume run stuck in `NEEDS_USER_INPUT` instead of finalizing when main-health is not applicable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add if health.status == skip: return None alongside pass in _emergency_repair_transient_recovery_result; extend python/tests/implement/test_ship.py with emergency-repair resume coverage asserting skip finalizes postmerge; list python/larch/implement/ship.py emergency-repair branch in ### UPDATED files if not already implied.


### [Plan Review] FINDING_2

### FINDING_2: Non-default workflow miss should stay error
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The main-health regression coverage does not prove that a `gh` "workflow not found" rc 1 is only downgraded to `skip` for the default CI workflow; a non-default workflow miss could be misclassified if the guard regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a test_main_health case: run_list_filtered_read rc 1 with could not find any workflows named Other and query.workflow Other (or non-default name) asserts status error not skip.

---LARCH-REJECTED-END---
