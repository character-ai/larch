## Proposed Design Outline

### Goals
- Guard `canonical_dir`, `marker_value`, and `marker_candidates` against drift between the two guard hooks.
- Fail CI when any of those three functions diverge between `hook-bg-poll-guard.sh` and `hook-no-progress-guard.sh`.

### Non-goals
- Behavioral-equivalence fixtures for the intentionally-renamed pairs (`marker_step_completed`/`is_step_completed`, `marker_is_live`/`is_marker_live`).
- Any behavior change in either hook script.

### Approach sketch
- Add three `compare_function` calls to `scripts/test-hook-clone-ownership-parity.sh` using the existing `compare_function` helper.
- Update `scripts/test-hook-clone-ownership-parity.md` to list all five guarded functions.

### Surfaces in scope
- `scripts/test-hook-clone-ownership-parity.sh`
- `scripts/test-hook-clone-ownership-parity.md`

### Open questions
- None.
