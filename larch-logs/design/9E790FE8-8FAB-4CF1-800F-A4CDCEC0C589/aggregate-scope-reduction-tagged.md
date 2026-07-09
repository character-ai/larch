### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/progress_file.py:326-343
- **Concern**: [SCOPE-REDUCTION] Append path need not open clone fd plus run subdir. Scenario: Step 5 routes `append_breadcrumb_for_run` through `_ensure_directory_fd(clone_dir)` and `_open_or_create_subdir`, but a single `_ensure_directory_fd(run_dir)` already fd-pins the full parent chain for append-only writes. That adds an extra fd, extra cleanup, and extra leak surface without improving the stated security goal; `_open_or_create_subdir` stays required only under a pinned clone fd in `activate_run`.
- **Proposed resolution**: For `append_breadcrumb_for_run` only, open with `_ensure_directory_fd(run_dir)`, append via `_append_line_in_dir`, and close in `finally`; keep clone fd plus `_open_or_create_subdir` solely in `activate_run`.
