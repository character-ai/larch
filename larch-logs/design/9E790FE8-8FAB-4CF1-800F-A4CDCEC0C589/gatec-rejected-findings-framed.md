---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Post-fd swap tests need positive write-through assertions
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The rewritten swap tests treat post-fd-acquisition swaps as refusal/negative-only cases, but the pinned-fd design means `activate_run()` and `append_breadcrumb_for_run()` should still succeed through the held fd and write into the renamed original directory. Negative checks alone can miss a broken write-through path or incorrectly enforce refusal after fd pinning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Add paired success assertions for both run-scoped writers: rename the real dir away, symlink the old path, complete the write, then assert current or breadcrumbs.log exists under the renamed real dir and remains absent under the outside target.`
  - From Cursor-Pragmatic: `Align the replaced swap tests with the cleanup model: swap after _ensure_directory_fd / _open_or_create_subdir returns, assert no writes under the outside target, and assert the write lands in the renamed original directory (or append_breadcrumb_for_run returns True with log content there). Drop "refusal must occur" for post-fd swap tests; keep refusal expectations only for pre-existing symlink/non-directory entries at open time.`
  - From Cursor-Requirements: `Rename/reframe post-fd swap tests as success cases: after rename-plus-symlink at the original path, assert activate_run succeeds and current lands in the renamed clone dir (not the outside target); assert append_breadcrumb_for_run returns True and the log lands in the renamed run dir. Reserve broadened OSError matching for pre-open symlink fixtures like test_activate_run_refuses_symlinked_run_dir_and_current only.`


### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/progress_file.py:326-343
- **Concern**: [SCOPE-REDUCTION] Append path need not open clone fd plus run subdir. Scenario: Step 5 routes `append_breadcrumb_for_run` through `_ensure_directory_fd(clone_dir)` and `_open_or_create_subdir`, but a single `_ensure_directory_fd(run_dir)` already fd-pins the full parent chain for append-only writes. That adds an extra fd, extra cleanup, and extra leak surface without improving the stated security goal; `_open_or_create_subdir` stays required only under a pinned clone fd in `activate_run`.
- **Proposed resolution**: For `append_breadcrumb_for_run` only, open with `_ensure_directory_fd(run_dir)`, append via `_append_line_in_dir`, and close in `finally`; keep clone fd plus `_open_or_create_subdir` solely in `activate_run`.

---LARCH-REJECTED-END---
