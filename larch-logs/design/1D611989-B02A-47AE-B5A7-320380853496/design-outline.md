## Proposed Design Outline

### Goals
- Flip the DEFAULT progress writer (`append_breadcrumb`) to follow the per-clone `current` pointer and append into `<clone-hash>/<run-id>/breadcrumbs.log`.
- Flip the statusline reader (`render_statusline` / `_age_suffix`) to follow the same pointer, so a fresh run starts empty and prior same-clone runs never render.
- Ignore legacy flat `<clone-hash>.log` in the reader; document the final per-run contract.

### Non-goals
- No changes to `activate_run`, cleanup/retention, or `progress note --run-id` (all landed in pieces 1–3).
- No concurrency guarding — one job per clone is a hard larch rule (single active run).
- No run-id plumbing through review/ship call sites; writers keep their signature.

### Approach sketch
- `append_breadcrumb`: resolve `current` via the existing pointer reader; valid pointer -> append via the run-scoped path; missing/invalid -> return `False` (fail-silent no-op).
- Reuse existing helpers (`_read_active_run_id` / `run_progress_path`), finally consuming the currently-unused `_read_active_run_id`.
- Reader: resolve the run-scoped log via the pointer; feed that path to `_tail_breadcrumbs` and `_age_suffix`; render nothing when pointer/subdir/file absent.
- Preserve symlink-safety (`assert_no_symlink_path_or_ancestors`, `O_NOFOLLOW`) and corruption fail-silent behavior.

### Surfaces in scope
- `python/larch/report/progress_file.py` (writer flip)
- `python/larch/report/statusline.py` (reader flip)
- `python/tests/report/test_progress_statusline.py` (acceptance tests)
- `docs/progress-reporting.md` (per-run contract)

### Open questions
- None. (Concurrency resolved: one job per clone.)
