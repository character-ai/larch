## Proposed Design Outline

### Goals
- Fix pre-arm cleanup gap in `checks_commit_route_main` so resumed tmpdirs don't release hook denial early (Item 1).
- Align Step 3 bg-wait timeout to `10800` across both `checks_commit_route_main` and `run_step_checks_main` (Item 2).
- Remove duplicate `_read_keepalive_clone_path` from `design_core.py` by importing from `bg_wait.py` (Item 3).
- Harden parity harness with richer exclusion comments and negative fixtures (Items 4, 5).
- Fix test to import `_write_bg_wait_marker` from `bg_wait` directly (Item 6).

### Non-goals
- Full consolidation of `_bg_wait_marker_context` write semantics into `_write_bg_wait_marker`.
- Behavior changes to any design-side marker writing beyond removing the duplicate helper.
- Changes to the `WRITERS` list (design_core.py still owns its own write).

### Approach sketch
- In `checks_commit_route_main`, add two `contextlib.suppress(OSError)` unlink calls before `_optional_bg_wait_marker` when `checks_site == "step3"`, mirroring `run_step_checks_main`.
- Change `15600` to `10800` in `_checks_commit_route_marker` for the step3 case.
- In `design_core.py`, remove `_read_keepalive_clone_path` and add `from larch.implement.bg_wait import _read_keepalive_clone_path`.
- In parity harness `.sh` and `.md`, extend the `marker_is_live`/`is_marker_live` exclusion comment to enumerate specific differing fields; add negative fixture function.
- In `test_implement_dispatch.py`, update the test to import `_write_bg_wait_marker` from `larch.implement.bg_wait` directly.

### Surfaces in scope
- `python/larch/implement/dispatch_commit_route.py`
- `python/larch/design/design_core.py`
- `scripts/test-hook-clone-ownership-parity.sh`
- `scripts/test-hook-clone-ownership-parity.md`
- `python/tests/implement/test_implement_dispatch.py`

### Open questions
- None.
