## Proposed Design Outline

### Goals
- Add `defer_push` / `has_bump` keyword inputs to `rebase_and_rebump` (gap #2), defaulting to today's behavior.
- Thread `base_remote`/`base_ref` into `apply_bump` so its fetch + version guard match the rebase guard (gap #3).
- Cover the new branches and base threading with unit / bash-parity tests.

### Non-goals
- Gap #1 pre-drop `refresh-run-logs` + `larch-logs/` fixup — deferred to the Phase 7 `ship.py` driver (#3240 amended).
- Changing `classify_bump`'s `origin/main` base (separate concern; not named by #3311).
- Wiring `rebase_and_rebump` into any live driver (Phase 7 owns cutover).

### Approach sketch
- `python/rebase.py`: add `defer_push: bool = False`, `has_bump: bool = True` (keyword-only); gate the classify/apply/changelog block on `has_bump`, gate the force-push on `not defer_push`; reflect skipped push in `RebaseResult.pushed`.
- `python/version_bump.py`: add `base_remote="origin"`, `base_ref="main"` params to `apply_bump`; replace the two hardcoded `origin/main` uses (fetch + guard `show_file`) with the base.
- `python/rebase.py:598`: pass `base_remote`/`base_ref` from `rebase_and_rebump` into `apply_bump`.
- Tests: extend `test_rebase.py` / `test_version_bump.py` for `defer_push`/`has_bump` branches + base-threaded guard.

### Surfaces in scope
- `python/rebase.py` (`rebase_and_rebump`)
- `python/version_bump.py` (`apply_bump`)
- `python/test_rebase.py`, `python/test_version_bump.py`

### Open questions
- None.
