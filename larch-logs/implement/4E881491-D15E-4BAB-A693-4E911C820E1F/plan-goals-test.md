## Goal
Implement issue #5313: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] SessionStart admin-merge hook lacks regression and security coverage.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt

**Phase**: implement

**Vote tally**: N/A


## Description

No regression test harness pins the new SessionStart hook's always-exit-0 or spawn contract, so hook registration or launch behavior regressions can ship undetected. `SECURITY.md` also omits the new SessionStart background admin-merge behavior, so operators auditing hook security surface would not see this shipped hook.
- **Suggested revisions (informational for voters; coder decides)**:
  - Add regression coverage for the SessionStart hook registration, always-exit-0 behavior, and background spawn contract.
  - Update `SECURITY.md` to document the SessionStart background admin-merge hook behavior.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
