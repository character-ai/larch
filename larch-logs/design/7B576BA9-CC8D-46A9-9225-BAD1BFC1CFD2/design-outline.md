## Proposed Design Outline

### Goals
- Arm `step-8-ship.sh` with a `.bg-wait-active` marker so both notification-storm hooks (poll-guard and no-progress circuit breaker) cover ship-pr.
- Register `implement-step8-ship` in both hooks' completion-release allowlists, using `.step-8-ship-handoff.rc` as the terminal sentinel.
- Allow the single sanctioned rc probe (`test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"`) while the marker is live, clamped against repeated absent-rc probes.

### Non-goals
- No changes to ship-pr business logic, `python/cli.py ship pr` argv, or sidecar contracts.
- No new orchestrator behaviors or threshold changes in the circuit breaker.
- No migration of other `/implement` steps to this mechanism.

### Approach sketch
- `step-8-ship.sh`: clear `no-progress-turns.count` / `no-progress-circuit-breaker-armed` at entry; write `.bg-wait-active` with `PID`, `START_EPOCH`, `TIMEOUT_S=21600`, `STEP=implement-step8-ship`; add `rm -f .bg-wait-active` to `persist_handoff` EXIT trap after the rc write (fail-open).
- `hook-bg-poll-guard.sh`: add `implement-step8-ship` to `marker_step_completed` (sentinel: `.step-8-ship-handoff.rc`) and `reset_probe_counter_for_step`; add `bash_is_step8_rc_foreground_probe` + `step8_rc_probe_clamp` functions; wire them before the generic deny loop.
- `hook-no-progress-guard.sh`: add `implement-step8-ship` to `is_step_completed` with `.step-8-ship-handoff.rc` sentinel.
- Tests: assert marker in `test-step-8-ship.sh`; add ship-pr deny+allow assertions in `test-hook-bg-poll-guard.sh`; add circuit-breaker arm+disarm assertions in `test-hook-no-progress-guard.sh`.
- Docs: update `step-8-ship.md` edit-in-sync list; update NEVER #8 in `skills/implement/SKILL.md` to note rc probe is now hook-allowed.

### Surfaces in scope
- `skills/implement/scripts/step-8-ship.sh`
- `scripts/hook-bg-poll-guard.sh`
- `scripts/hook-no-progress-guard.sh`
- `scripts/test-hook-bg-poll-guard.sh`
- `scripts/test-hook-no-progress-guard.sh`
- `skills/implement/scripts/test-step-8-ship.sh`
- `skills/implement/SKILL.md` (NEVER #8 only)
- `skills/implement/scripts/step-8-ship.md`

### Open questions
- None.
