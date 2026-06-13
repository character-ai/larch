## Proposed Design Outline

### Goals
- Ensure all descendant processes of `design-step3-review.sh` are killed when the wrapper exits, regardless of exit reason.
- Prevent `plan.txt` and other session artifacts from being modified after the orchestrator receives the background-task notification.

### Non-goals
- Fixing the underlying Cursor timeout mechanism in `launch-review.sh` or `run_external_agent`.
- Preventing orphans spawned in new sessions via `setsid` (a Cursor-internal behavior outside larch's control).

### Approach sketch
- Enable job control (`set -m`) in `design-step3-review.sh` so `run-step3-review.sh` launched with `&` gets its own process group.
- Install an EXIT trap that sends `kill -- -"$_loop_pid"` (process-group SIGTERM) on any exit of the wrapper.
- Change the synchronous invocation to background + `wait`, capturing the PID in `_loop_pid`.
- Clear the trap after `wait` returns normally and restore `set +m`.
- Add structure pins to `test-design-structure.sh` confirming `_loop_pid=` and `kill -- -"$_loop_pid"` are present.

### Surfaces in scope
- `skills/design/scripts/design-step3-review.sh` — the wrapper that launches `run-step3-review.sh`
- `scripts/test-design-structure.sh` — structure regression guard

### Open questions
- None.
