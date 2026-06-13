## Proposed Design Outline

### Goals
- Fix `kill_session_background_processes` in both bash and Python to skip the full ancestor PID chain, not just the immediate parent.
- Add a breadcrumb log to `_write_terminal_finalize_if_terminal` confirming the write completed.

### Non-goals
- No change to the `restore-finalize-state` fallback path (it handles recovery correctly).
- No fsync hardening in `_write_finalize_text_safely` (lower-probability APFS hypothesis).
- No behavioral change to Step 18 branching or `finalize-state.sh` content.

### Approach sketch
- In `scripts/implement-finalize.sh`: add `_collect_ancestor_pids` (depth-capped walk via `ps -o ppid=`); update `kill_session_background_processes` to skip all collected ancestors.
- In `python/finalize.py`: add `_collect_ancestor_pids` helper; expand the `skip` set in `kill_session_background_processes` to include all ancestors.
- In `python/ship.py`: add `_breadcrumb("finalize-state-written", ...)` at the end of `_write_terminal_finalize_if_terminal`.
- Add bash-level test verifying an ancestor process (grandparent invoking teardown) is not killed.
- Update `scripts/implement-finalize.md` to reflect updated skip semantics.

### Surfaces in scope
- `scripts/implement-finalize.sh`
- `python/finalize.py`
- `python/ship.py`
- `scripts/test-implement-finalize.sh`
- `scripts/implement-finalize.md`

### Open questions
- None.
