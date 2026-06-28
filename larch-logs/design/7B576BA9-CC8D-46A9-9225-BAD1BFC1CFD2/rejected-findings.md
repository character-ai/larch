### [Plan Review] FINDING_2

### FINDING_2: Plan omits `test-implement-structure.sh` contract enforcement
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan mandates a separate foreground stale-handoff `rm` before every Step 8+ `run_in_background` launch but does not update `scripts/test-implement-structure.sh`, the repo's SKILL.md contract linter (`require`/`require_near` pins for Step 8 launcher, handoff gates, conflict-resolution re-entry). Wrapper entry cleanup and hook tests can pass while `SKILL.md` or `conflict-resolution.md` omits or drifts the orchestrator-only clear; `test-implement-fence-shape.sh` only guards single-line launcher fences. Reship/ci-fix/stall-recovery relaunches can still satisfy a stale `.step-8-ship-handoff.rc` probe before the new wrapper runs, reproducing the stale-handoff misroute risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: scripts/test-implement-structure.sh`: `require()` the foreground `rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json"` prose in `skills/implement/SKILL.md`; `require_near()` placing that clear before the single-line `step-8-ship.sh` launcher; extend the existing `conflict-resolution.md` needles loop (~447-455) with the same clear-then-launcher ordering. Include `bash scripts/test-implement-structure.sh` in Testing strategy.

