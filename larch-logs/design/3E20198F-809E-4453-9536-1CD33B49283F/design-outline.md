## Proposed Design Outline

### Goals
- Fix the spurious "dropped" notice in `_architectural_guidelines_section`: display the note when it is present but non-consumable due to post-merge HEAD drift.
- Add `note_readable_any_head(implement_tmpdir)` helper to `architectural_guidelines.py` that reads the durable note by `STATUS` only, without HEAD_SHA equality.
- Clear the spurious `DROPPED_NOTE_ARTIFACT` file and skip `_persist_drop_notice_and_invalidate` when the post-merge fallback reads the note successfully.
- Guard `_pin_architectural_guidelines_note_best_effort` so it does not attempt a re-pin on main HEAD after `git checkout main`.

### Non-goals
- Do not change `note_consumable()`: it is correct for the ship-loop context.
- Do not change `_local_cleanup` or `git checkout main` behavior.
- Do not add new sentinel files to finalize.py to signal post-merge state.

### Approach sketch
- Add `note_readable_any_head(implement_tmpdir: Path) -> bool` to `architectural_guidelines.py`: open the durable-note metadata file, return `True` when `STATUS == "present"`, ignoring `HEAD_SHA`.
- In `_architectural_guidelines_section` (`final_report.py`): when `has_guideline_artifacts and not consumable`, call `note_readable_any_head`; on `True`, read and display the note content; skip `_persist_drop_notice_and_invalidate`; remove `DROPPED_NOTE_ARTIFACT` if present.
- In the step-16-17 pathway, guard `_pin_architectural_guidelines_note_best_effort`: detect post-merge HEAD state by comparing current HEAD SHA against the durable note's `HEAD_SHA`; if current HEAD is not on the implementation branch, skip the pin attempt and log a breadcrumb.
- Add unit tests for `note_readable_any_head` and for the updated `_architectural_guidelines_section` branch.

### Surfaces in scope
- `python/larch/core/architectural_guidelines.py` — new `note_readable_any_head` helper
- `python/larch/report/final_report.py` — updated `_architectural_guidelines_section`
- `python/larch/ship/` or step-16-17 module — guard on `_pin_architectural_guidelines_note_best_effort`
- Test file(s) for the above modules

### Open questions
- None.
