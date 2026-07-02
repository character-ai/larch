## Proposed Design Outline

### Goals
- Make `refresh_staged_assessment_for_current_head` actually recover on fingerprint drift instead of always returning `False`.
- Flip the two tests that currently pin the wrong (drop) behavior into recovery assertions.
- Restore the guideline note surviving ship-time HEAD drift, per #5675's original acceptance criterion.

### Non-goals
- No prompt-side or LLM re-assessment of guideline content. The staged assessment text is carried forward unchanged; only fingerprint/HEAD metadata is refreshed.
- No change to `ship_guidelines.py`'s call-site retry logic (`_pin_and_load_guidelines_note`); it already retries correctly once refresh succeeds.
- No #5754 `note_readable_any_head` fallback wiring into ship-time pinning (optional item from the issue; deferred per Step 1c resolution).

### Approach sketch
- `python/larch/core/architectural_guidelines.py`: remove the erroneous `fingerprint != stored_fp` bail in `refresh_staged_assessment_for_current_head` (~line 500) so drift triggers recovery (recompute live fingerprint/diff, rewrite the staged snapshot, return `True`) instead of bailing.
- Keep all other fail-closed exits (missing artifacts, no repo root, unresolved base ref, live-diff materialization failure, I/O failure) unchanged.
- `python/tests/core/test_architectural_guidelines.py`: flip `test_refresh_staged_assessment_for_current_head_returns_false_when_diff_changes` to assert successful recovery and updated staged metadata.
- `python/tests/implement/test_ship.py`: flip `test_pin_and_load_guidelines_note_returns_drop_notice_when_diff_changes_with_repo` to assert the note survives (not dropped) when repo_root is available and the diff drifted.

### Surfaces in scope
- python/larch/core/architectural_guidelines.py
- python/tests/core/test_architectural_guidelines.py
- python/tests/implement/test_ship.py

### Open questions
- None.
