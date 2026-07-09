## Proposed Design Outline

### Goals
- Close the TOCTOU gap in `activate_run()` and `append_breadcrumb_for_run()` by keeping the verified directory fd live through the final write.
- Eliminate the redundant path-based symlink re-checks that bracket `_ensure_directory` calls in those two functions.

### Non-goals
- Fix `append_breadcrumb()` (flat breadcrumb path; not mentioned in the issue).
- Change any public API or caller behavior.
- Touch any file outside `progress_file.py` and its test module.

### Approach sketch
- Add `_ensure_directory_fd(path: Path) -> int`: same traversal as `_ensure_directory` but returns the final directory fd instead of closing it.
- Add `_open_or_create_subdir(parent_fd: int, name: str) -> int`: fd-relative single-level mkdir+open.
- Rewrite `_ensure_directory` to delegate to `_ensure_directory_fd` and immediately close the fd.
- Rewrite `activate_run` to hold `clone_dir_fd` from `_ensure_directory_fd`, create `run_id` subdir via `_open_or_create_subdir`, write `current` via `clone_dir_fd`.
- Rewrite `append_breadcrumb_for_run` to hold `clone_dir_fd`, open/create `run_id` subdir fd, append via that fd.
- Update tests that traced `_open_verified_dir` in these two functions.

### Surfaces in scope
- `python/larch/report/progress_file.py`
- `python/tests/report/test_progress_statusline.py`

### Open questions
- None.
