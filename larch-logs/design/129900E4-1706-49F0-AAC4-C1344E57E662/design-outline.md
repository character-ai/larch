## Proposed Design Outline

### Goals
- Restore `breadcrumbs/quiet.log` publishing for every implement and design run.
- Fix both the outer gate (`_publish_breadcrumbs_with_warning`) and the inner guard (`publish_breadcrumbs_main`) that together block staging when `breadcrumbs/` was never created.
- Add regression tests that verify publishing works without a pre-created `breadcrumbs/` directory.

### Non-goals
- No changes to `quiet_init` or `PATH_QUIET_LOG_TEMPLATE` (write path is correct).
- No changes to `docs/run-logs.md` (the documented contract is already correct).
- No changes to the redaction pipeline, symlink/hardlink guards, or `_breadcrumb_source_confined`.
- No creation of `<session-tmpdir>/breadcrumbs/` in session bootstrap (the docs say creation should not be required).

### Approach sketch
- In `_publish_breadcrumbs_with_warning` (line 1876): change `if not (bread_src.is_dir() and log_root.name == "larch-logs"):` to `if log_root.name != "larch-logs":` — drop the `bread_src.is_dir()` guard.
- In `publish_breadcrumbs_main` (lines 2225-2227): remove the `if not src.is_dir(): return 1` block; `source_root = src.parent` already computes the right scan directory even when `src` does not exist.
- Update `test_commit_run_warns_when_breadcrumb_publish_returns_nonzero` to not create `breadcrumbs/` (verify the outer gate no longer requires it).
- Add `test_commit_run_publishes_breadcrumbs_without_breadcrumbs_dir` and `test_publish_breadcrumbs_main_succeeds_without_breadcrumbs_dir` to prove the full path works end-to-end.

### Surfaces in scope
- `python/larch/report/run_logs.py` (functions `_publish_breadcrumbs_with_warning` and `publish_breadcrumbs_main`)
- `python/test_run_logs.py` (update one existing test; add two new tests)

### Open questions
- None.
