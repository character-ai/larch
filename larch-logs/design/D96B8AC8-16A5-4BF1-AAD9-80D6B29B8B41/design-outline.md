## Proposed Design Outline

### Goals
- Prevent stale `.design-step0-route-state.env` REPO from leaking into fresh Step 0b invocations.
- Ensure `resolve_repo()` is always called when ISSUE_NUMBER is explicitly provided.

### Non-goals
- Changing resume path behavior: resumes still use `_recover_resume_route_state_values` correctly via `_refresh_resume_source_env`.
- Modifying the route-state file format or the REPO emission logic in `_finish_step0_route`.
- Adding new env vars or CLI flags.

### Approach sketch
- Change one condition in `_bind_step0_route_issue_env` from `or` to `and`.
- On a fresh call with explicit ISSUE_NUMBER, the `and` condition is False so gap-fill is skipped.
- `resolve_repo()` then provides the correct REPO at line 512-513.
- Add one regression test that seeds stale REPO in route-state and verifies it is not used.

### Surfaces in scope
- `python/larch/design/design_step0.py` (1-line condition change)
- `python/tests/design/test_design_lifecycle.py` (1 regression test)

### Open questions
- None.
