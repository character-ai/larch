## Proposed Design Outline

### Goals
- Eliminate the ~87% drop rate of the architectural-guideline note by re-staging the assessment on HEAD drift instead of dropping it.
- Keep the existing assessment text; only refresh the diff fingerprint against current HEAD.

### Non-goals
- Full orchestrator re-assessment (requires human involvement; treated as fallback only).
- Changes to Step 7a assessment staging or any other guideline helpers.
- Changes to the fallback drop-notice behavior (preserved when re-staging itself fails).

### Approach sketch
- Add `re_stage_on_drift(implement_tmpdir, *, base_ref, repo_root)` to `architectural_guidelines.py`.
  - Reads existing staged assessment text, re-materializes diff via `materialize_implementation_diff`, updates sidecar fingerprint.
  - Returns True on success, False on any failure (caller handles both paths).
- In `_pin_and_load_guidelines_note` (ship.py): when `pin_note_from_staged` returns False, call `re_stage_on_drift`; if it succeeds, retry `pin_note_from_staged`; log a warning and fall through to drop only if still False.
- Add unit tests for `re_stage_on_drift` and the retry behavior.

### Surfaces in scope
- `python/larch/core/architectural_guidelines.py`
- `python/larch/implement/ship.py`
- `python/test_architectural_guidelines.py`
- `python/test_ship.py`

### Open questions
- None.
