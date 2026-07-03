## Decision 1: Site scope — all 4 reachable call sites
- **Question**: Should this PR also fix ci_monitor.py:1625 and ci_agentic_fix.py's two call sites (lines 501/726), or stay scoped to the two ship_merge.py sites (lines 219, 251) the issue names as primary? (Investigation confirmed all four share the identical unconditional-invalidate-without-pin shape and are reachable, not just speculative.)
- **Resolution**: Fix all 4 reachable call sites in this PR: `ship_merge.py`'s `_ship_rebase_phase` (line 219) and `_ship_phase14_rebase` (line 251), `ci_monitor.py`'s `_invalidate_guidelines_before_push` (line 1625), and `ci_agentic_fix.py`'s `_invalidate_guidelines_before_ci_push` (used at lines 501 and 726). Closes the whole bug class at once rather than risking a 9th recurrence issue.
- **Source**: user

## Decision 2: Fix shape — shared helper
- **Question**: Call `pin_note_from_staged_for_current_head` directly inline at each fixed site, or introduce a shared `try_pin_or_invalidate()` helper?
- **Resolution**: Add one shared `try_pin_or_invalidate()` helper (issue's suggested fix #4) and route all 4 fixed call sites through it. Likely lives in `ship_guidelines.py` alongside `_invalidate_guidelines_note` and `_pin_and_load_guidelines_note`.
- **Source**: user

## Decision 3: Dead code cleanup — bundled into this PR
- **Question**: Bundle the unrelated dead `monitor.did_fixing` cleanup (`ship.py:847-849` + `ci_monitor.py` plumbing) into this PR?
- **Resolution**: Remove it in this PR: the dead `if monitor.did_fixing: _invalidate_guidelines_note(...)` branch in `ship.py` (~847-849), and the always-`False` `did_fixing` field plumbing in `ci_monitor.py` (field declaration + all construction sites).
- **Source**: user
