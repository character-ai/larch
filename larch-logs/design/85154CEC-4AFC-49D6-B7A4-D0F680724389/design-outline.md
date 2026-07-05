## Proposed Design Outline

### Goals
- Fix `_classify_ship_outcome` so `guidelines_status` comes from materialized metadata, not note-emptiness inference (Findings 1 & 3).
- Add `pr: int = 0` to `implement_step8_reachable` and thread it to `_manifest_bail_signal` so bail-with-PR evidence resolves correctly (Finding 2).
- Guard `write_guideline_ship_outcome` against empty `head_sha` and validate `head_sha` non-emptiness in `validate_guideline_ship_outcome_record` (Finding 4).
- Fix gc-slimmed exemption to reject broken or regular symlinks, not only truly absent artifacts (Finding 5).

### Non-goals
- No changes to other audit scan handlers or ship-pr orchestration beyond the targeted surfaces.
- No migration or back-fill of existing committed run-log artifacts.
- No changes to forked-target paths beyond what the `head_sha` guard naturally covers.

### Approach sketch
- `_classify_ship_outcome`: remove the note-emptiness fallback; when `guidelines_status` is not in `{"present","absent","invalid"}`, treat it as `"absent"` directly rather than inferring from `result.note`.
- `write_guideline_ship_outcome`: add an early return when `head_sha` is empty, logging a warning via `_log_guidelines_ship_warning`.
- `implement_step8_reachable`: add `pr: int = 0` parameter; forward it to all `_manifest_bail_signal` calls inside the function.
- `_guideline_ship_outcome_scan_obj`: pass `pr` to `implement_step8_reachable`; tighten the gc-slimmed exemption to use `not path.exists() and not path.is_symlink()` (artifact truly absent).
- `validate_guideline_ship_outcome_record`: add a `not head_sha` check alongside the existing `base_ref` check.

### Surfaces in scope
- `python/larch/implement/ship_guidelines.py`
- `python/larch/issue/audit_runs.py`
- `python/larch/core/architectural_guidelines.py`
- `python/tests/implement/test_ship.py`
- `python/tests/issue/test_audit_runs.py`
- `python/tests/core/test_architectural_guidelines.py`

### Open questions
- None.
