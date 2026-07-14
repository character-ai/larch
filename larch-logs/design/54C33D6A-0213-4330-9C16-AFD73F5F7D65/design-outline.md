## Proposed Design Outline

### Goals
- Replace the last raw `["gh", "issue", "view", ...]` argv call in `voter-calibration.py` with `gh.issue_view_field_read(proc, ...)` to complete the umbrella scope.
- Delete the now-unused `_run_gh_json` helper.

### Non-goals
- Extend `gh-argv-literal` lint scope to `skills/` Python files.
- Change bulk issue listing in voter-calibration.py (already uses `fetch_main`).
- Modify any `python/larch/` module.

### Approach sketch
- Add `from larch.core import proc` and `from larch.git import gh` imports.
- Replace `_run_gh_json(["gh", "issue", "view", ..., "--json", issue_fields])` with `gh.issue_view_field_read(proc, issue, issue_fields, repo=repo)`.
- Adapt error handling: catch `FileNotFoundError`, `ShipError`, `TransientNetworkError`; check `result.returncode != 0`; parse `result.stdout` as JSON.
- Delete `_run_gh_json`.

### Surfaces in scope
- `skills/voter-calibration/scripts/voter-calibration.py` (lines 178-215)

### Open questions
- None.
