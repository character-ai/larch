### [Plan Review] FINDING_1

### FINDING_1: Missing structure-harness pins for Step 8 ordering
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan updates the fence-shape checks but not the structure harness that enforces branch and registry ordering, so the new pre-fix step can still ship without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: scripts/test-implement-structure.sh with require_text / require_near pins that ship pre-fix-rebase appears in the ci-fix and reship SKILL slices before ship-pr-ci-fix.md and before the stale-handoff clear / step-8-ship.sh relaunch.
  - From Cursor-Pragmatic: Add ### UPDATED: scripts/test-implement-structure.sh with pins for the new CLI registry, machine-stdout membership, and ci-fix/reship slices requiring python/cli.py ship pre-fix-rebase before stale-handoff clear and before loading ship-pr-ci-fix.md


### [Plan Review] FINDING_3

### FINDING_3: Route-exit still exposes ci-fix/reship before the Python gate
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The route-exit boundary can still emit autonomous ci-fix or reship actions before the new Python gate runs, so the required rebase ordering remains prose-dependent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Have ship_route_exit_main route ci-fix and non-phase14 reship through the pre-fix rebase helper before emitting the final autonomous action, or emit only a Python-owned intermediate action that cannot reach repair until PRE_FIX_REBASE_STATUS=ok


