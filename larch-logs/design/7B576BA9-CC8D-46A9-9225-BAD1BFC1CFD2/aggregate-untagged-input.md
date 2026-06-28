### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:44-45; skills/implement/references/ship-pr-ci-fix.md:5-23; skills/implement/references/conflict-resolution.md:5-15,107; skills/implement/references/ship-pr-exit-matrix.md:39-58
- **Concern**: The plan updates `skills/implement/SKILL.md` but still leaves the load-on-demand Step 8+ relaunch docs stale. These files are the actual prompts loaded on `step8-shippr`, `ci-fix`, conflict-resolution re-entry, and `reship`.. Scenario: Those routes can still re-invoke `step-8-ship.sh` without the new foreground pre-launch `rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json" 2>/dev/null || true`, so stale sidecars can misroute premature notifications before wrapper-entry cleanup runs.
- **Proposed resolution**: Add these docs to `### UPDATED` and mirror the same foreground pre-launch clear in each re-entry block, not just in `SKILL.md`.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh
- **Concern**: The plan mandates a separate foreground stale-handoff `rm` before every Step 8+ `run_in_background` launch but does not update `test-implement-structure.sh`, which is the repo’s SKILL.md contract linter (`require`/`require_near` pins for Step 8 launcher, handoff gates, conflict-resolution re-entry).. Scenario: Wrapper entry cleanup and hook tests can pass while SKILL.md (or `conflict-resolution.md`) omits or drifts the orchestrator-only clear; `test-implement-fence-shape.sh` only guards single-line launcher fences. Reship/ci-fix/stall-recovery relaunches can still satisfy a stale `.step-8-ship-handoff.rc` probe before the new wrapper runs, reproducing round-3 FINDING_1.
- **Proposed resolution**: Add `### UPDATED: scripts/test-implement-structure.sh`: `require()` the foreground `rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json"` prose in `skills/implement/SKILL.md`; `require_near()` placing that clear before the single-line `step-8-ship.sh` launcher; extend the existing `conflict-resolution.md` needles loop (~447-455) with the same clear-then-launcher ordering. Include `bash scripts/test-implement-structure.sh` in Testing strategy.

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:39-41,56-58; skills/implement/references/ship-pr-ci-fix.md:5,23; skills/implement/references/conflict-resolution.md:5,7,15; skills/implement/references/stall-recovery.md:44-45
- **Concern**: Missing foreground pre-launch clear in the actual Step 8 re-entry docs. Scenario: These are the branches that actually re-invoke `step-8-ship.sh`. The plan only patches `skills/implement/SKILL.md` and `skills/implement/scripts/step-8-ship.md`, so the load-on-demand docs still tell operators to relaunch ship-pr without the required separate `rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json" 2>/dev/null || true` clear. A premature `<task-notification>` on reship, ci-fix, conflict-resolution, or `step8-shippr` can still follow stale instructions.
- **Proposed resolution**: Add the four re-entry docs to `### UPDATED:` and insert the same separate foreground sidecar-clear step immediately before each `step-8-ship.sh` re-invoke bullet.
