### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py:121-150
- **Concern**: Default append still authorizes `_ensure_directory_fd` for the clone dir before `current` is validated. Scenario: The implementation shape lists `_ensure_directory_fd` first (with `_open_verified_dir` only when the clone dir already exists). That creates `progress/<clone-hash>/` on missing or invalid `current`, breaking the edge-case contract that missing clone/pointer appends fail silent with no side effects; missing-current acceptance only checks return value, empty statusline, and no flat log, so this regression can pass tests
- **Proposed resolution**: Mandate `_open_verified_dir(clone_dir)` only for default `append_breadcrumb` (return `False` on `OSError`); read `current` via `_read_active_run_id_from_dirfd`; only then `_open_or_create_subdir` for the active run. Drop `_ensure_directory_fd` from the default-append path. Optionally `[SCOPE-REDUCTION]`: after `breadcrumb_line`, gate on `read_active_run_id(repo_root)` and delegate to `append_breadcrumb_for_run` so clone-open semantics stay aligned with the public reader

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/progress_file.py:121-354
- **Concern**: Plan re-specifies a second fd-append pipeline instead of reusing the explicit override writer. Scenario: `append_breadcrumb_for_run` already implements fd-anchored run-dir open, log append, and fail-silent `OSError`/`ValueError` handling. Re-documenting the same steps in `append_breadcrumb` adds duplicate logic and raises drift risk against the accepted TOCTOU pin test that mirrors the `for_run` helper
- **Proposed resolution**: The plan should describe default append as: validate with `breadcrumb_line`, return `False` when `read_active_run_id(repo_root)` is `None`, else call `append_breadcrumb_for_run(repo_root, run_id, skill, step, text)` unchanged. Keep the new fd-pin test on `append_breadcrumb` because it still exercises the production entrypoint

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:34-38
- **Concern**: Default append still allows a mkdir path on the fail-silent code path. Scenario: If `current` is missing or the clone progress tree is absent, using `_ensure_directory_fd` can create `progress/<hash>/` before returning `False`, which leaves orphan state and breaks the required no-op behavior for default writes
- **Proposed resolution**: Require `_open_verified_dir(clone_dir)` for `append_breadcrumb`, or explicitly preflight and bail before any directory creation; reserve `_ensure_directory_fd` for activation paths only

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: security
- **Location**: python/tests/report/test_progress_statusline.py:550-565
- **Concern**: `test_statusline_refuses_symlinked_progress_ancestors` still seeds a flat `progress_path` log and never sets an active `current`, so it can pass after the flip without exercising the new symlink-safe active-run reader.. Scenario: A broken `current`-based statusline path could regress on symlinked ancestors, and this test would not catch it because the flat log is ignored.
- **Proposed resolution**: Retarget the test to activate a run and place the symlink on the active-run `current` or run-log ancestor chain, then assert `render_statusline` still returns `""`.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/report/progress_file.py:230-241
- **Concern**: Statusline active-run reader still uses path-based clone-dir open. Scenario: The plan fixes the private current-file read, but `read_active_run_id` is specified to call `_open_verified_dir(clone_dir)`. That helper checks ancestors by path before `os.open`, so a symlink ancestor swap between check and open can still make `render_statusline` read another tree's `current` and breadcrumbs. This leaves the prior accepted fd-safe lookup fix incomplete.
- **Proposed resolution**: Add a no-create fd-relative opener for existing clone dirs, mirroring `_ensure_directory_fd` traversal without mkdir, and use it in `read_active_run_id`; return `None` on missing components.
