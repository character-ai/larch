## Proposed Design Outline

### Goals
- Add direct unit tests for `pin_note_from_staged_for_current_head` and `_pin_note_from_live_diff` in `python/larch/core/architectural_guidelines.py`.
- Add ship-level structural/failure/drift tests to `python/tests/implement/test_ship.py`: empty fingerprints, write failures, and a genuinely mutating fake repo across pin attempts.

### Non-goals
- No production code changes to `architectural_guidelines.py` or `ship.py`.
- No new shared test helpers or fixture modules beyond what the two target test files already use.

### Approach sketch
- Extend `python/tests/core/test_architectural_guidelines.py` (existing home for direct helper coverage) with new test functions for the two target helpers, reusing its `_repo`/`_git` fixtures and `ag.write_staged_assessment` setup pattern.
- Extend the `test_pin_and_load_guidelines_note_*` family in `python/tests/implement/test_ship.py` with: an empty-`DIFF_FINGERPRINT` case, a write-failure case, and a real-git-repo case that advances `origin/main` (via `git update-ref`) between two separate pin attempts.
- Match each file's existing monkeypatch/fixture conventions; no new abstractions.

### Surfaces in scope
- `python/tests/core/test_architectural_guidelines.py`
- `python/tests/implement/test_ship.py`

### Open questions
- None.
