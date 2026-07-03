## Proposed Design Outline

### Goals
- Stop the architectural-guidelines note from being dropped at any of the 4 confirmed invalidation call sites by attempting a pin-from-staged re-stage before falling back to invalidate.
- Consolidate the "try pin, then invalidate" sequence into one shared helper reused by all 4 fixed call sites, instead of repeating the pattern ad hoc.
- Remove the confirmed-dead `monitor.did_fixing` branch and its always-`False` plumbing while in this code.

### Non-goals
- No refactor of the two already-hardened call sites (`ship_guidelines.py`'s `_pin_and_load_guidelines_note`, `closeout.py`'s `_pin_architectural_guidelines_note_best_effort`) — they already pin correctly with logic suited to their own call contexts.
- No new regression-test harness spanning all 6 call sites uniformly; tests are added per touched module using existing patterns.
- No behavior change to rebase logic, CI-fix retry mechanics, or push semantics themselves — only guidelines-note handling after those operations succeed.

### Approach sketch
- Add a shared `try_pin_or_invalidate(...)` helper to `ship_guidelines.py`, wrapping `architectural_guidelines.pin_note_from_staged_for_current_head` with a fallback to the existing `_invalidate_guidelines_note` when the pin attempt returns `False`.
- Update `ship_merge.py`'s `_ship_rebase_phase` (line 219) and `_ship_phase14_rebase` (line 251) to call the new helper instead of invalidating directly, resolving a fresh post-rebase HEAD via existing `git` Runner helpers.
- Update `ci_monitor.py`'s `_invalidate_guidelines_before_push` (line 1625) and `ci_agentic_fix.py`'s `_invalidate_guidelines_before_ci_push` (line 101; covers both call sites at 501/726) the same way.
- Remove the dead `if monitor.did_fixing:` branch in `ship.py` (~847-849) and the always-`False` `did_fixing` field/plumbing in `ci_monitor.py`.
- Extend unit tests per touched module asserting a pin attempt happens before any fallback invalidate.

### Surfaces in scope
- `python/larch/implement/ship_guidelines.py` (new shared helper)
- `python/larch/implement/ship_merge.py` (2 call sites)
- `python/larch/implement/ci_monitor.py` (1 call site + dead `did_fixing` plumbing)
- `python/larch/implement/ci_agentic_fix.py` (1 function, 2 call sites)
- `python/larch/implement/ship.py` (dead code branch)
- `python/tests/implement/` (corresponding test files)

### Open questions
- None.
