## Proposed Design Outline

### Goals
- Include `.completed/` in the pause snapshot so restored tmpdirs have completion sentinels.
- Ensure Step 5c provenance guard passes on resumed runs where review is complete.
- Cover the round-trip in a new test.

### Non-goals
- Changing the resume step-determination logic in `_determine_step`.
- Modifying the Step 5c provenance guard itself.
- Fixing any other pause/resume bug beyond the snapshot omission.

### Approach sketch
- Remove `.completed` from `_PUBLISH_EXCLUDE_DIRS` in `design_log_publish_flow.py`.
- Update the adjacent comment to drop the mention of `.completed`.
- Add `test_publish_excluded_does_not_exclude_completed_dir` to verify the fix.
- Add `test_pause_load_step5c_restores_step3_sentinel` to verify round-trip restoration.

### Surfaces in scope
- `python/larch/design/design_log_publish_flow.py` (exclude set and comment)
- `python/tests/design/test_design_pause.py` (two new tests)

### Open questions
- None.
