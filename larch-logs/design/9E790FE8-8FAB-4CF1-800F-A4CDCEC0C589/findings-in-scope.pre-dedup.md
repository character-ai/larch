### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/report/test_progress_statusline.py
- **Concern**: Post-fd swap tests still lack positive write-through proof. Scenario: Round 1 FINDING_2 is only partly addressed: the plan replaces swap hooks and adds negative side-effect checks (`assert not (target / …).exists()`), but never requires that after clone or run dir rename plus symlink at the original path, `activate_run` writes `current` or `append_breadcrumb_for_run` appends via the held fd into the renamed real directory. An implementation that fails closed or no-ops after swap can still pass negative-only tests while breaking the core TOCTOU fix; `test_cleanup_old_progress_files_pins_clone_dir_before_enumeration` already shows the positive pinned-fd pattern.
- **Proposed resolution**: Add paired success assertions for both run-scoped writers: rename the real dir away, symlink the old path, complete the write, then assert `current` or `breadcrumbs.log` exists under the renamed real dir and remains absent under the outside target.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py:326-343
- **Concern**: `append_breadcrumb_for_run` plan omits explicit `validate_run_id` before subdir open. Scenario: Step 4 binds `safe_run_id = validate_run_id(run_id)` for `activate_run`; Step 5 only says preserve validation and pass `run_id` into `_open_or_create_subdir`, which calls `_validate_dir_entry_name` but not `_RUN_ID_PATTERN` or reserved-name checks. Values like `bad id` currently return `False` via `ValueError`; without `validate_run_id` they could create odd directory entries instead.
- **Proposed resolution**: In Step 5, bind `safe_run_id = validate_run_id(run_id)` immediately after building the breadcrumb line and pass only `safe_run_id` to `_open_or_create_subdir`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/progress_file.py:326-343
- **Concern**: [SCOPE-REDUCTION] Append path need not open clone fd plus run subdir. Scenario: Step 5 routes `append_breadcrumb_for_run` through `_ensure_directory_fd(clone_dir)` and `_open_or_create_subdir`, but a single `_ensure_directory_fd(run_dir)` already fd-pins the full parent chain for append-only writes. That adds an extra fd, extra cleanup, and extra leak surface without improving the stated security goal; `_open_or_create_subdir` stays required only under a pinned clone fd in `activate_run`.
- **Proposed resolution**: For `append_breadcrumb_for_run` only, open with `_ensure_directory_fd(run_dir)`, append via `_append_line_in_dir`, and close in `finally`; keep clone fd plus `_open_or_create_subdir` solely in `activate_run`.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_progress_statusline.py
- **Concern**: Post-fd clone/run swap tests contradict the cleanup pinned-fd success model. Scenario: The plan replaces path-based swap hooks with post-fd-acquisition swaps, but also lists the replaced swap test under "refusal must occur" while only requiring `assert not (target / ...).exists()`. After fd pinning, `activate_run` and `append_breadcrumb_for_run` should succeed through the held fd and write into the renamed real directory (see `test_cleanup_old_progress_files_pins_clone_dir_before_enumeration`), not raise. Tests that still expect `pytest.raises(OSError)` will fail on a correct implementation.
- **Proposed resolution**: Align the replaced swap tests with the cleanup model: swap after `_ensure_directory_fd` / `_open_or_create_subdir` returns, assert no writes under the outside target, and assert the write lands in the renamed original directory (or `append_breadcrumb_for_run` returns True with log content there). Drop "refusal must occur" for post-fd swap tests; keep refusal expectations only for pre-existing symlink/non-directory entries at open time.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py:326-343
- **Concern**: `append_breadcrumb_for_run` plan omits an explicit `validate_run_id` step before subdir creation. Scenario: Step 4 requires `validate_run_id` once in `activate_run`, but step 5 only says "preserving current validation" before fd opens. `_validate_dir_entry_name` accepts reserved names like `current`; without an early `validate_run_id`, `_open_or_create_subdir` could try to create a `current/` directory beside the `current` pointer file, changing reserved-name behavior.
- **Proposed resolution**: Add an explicit step-5 bullet: call `validate_run_id(run_id)` (bind `safe_run_id`) before `_open_or_create_subdir`, matching step 4. ## Findings 1. **correctness** (`python/tests/report/test_progress_statusline.py`): Post-fd swap tests contradict the cleanup pinned-fd success model. The plan both replaces swap tests with post-fd hooks and tells them to expect refusal, but fd-pinned writes should succeed into the renamed real directory while avoiding the outside symlink target. 2. **correctness** (`python/larch/report/progress_file.py:326-343`): `append_breadcrumb_for_run` should call `validate_run_id` explicitly before `_open_or_create_subdir`, as `activate_run` does. `_validate_dir_entry_name` alone does not reject reserved run IDs like `current`.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py:326-343
- **Concern**: Step 5 omits explicit validate_run_id before fd subdir open. Scenario: activate_run step 4 requires validate_run_id once; append rewrite drops run_progress_dir and only passes run_id to _open_or_create_subdir. _validate_dir_entry_name accepts "current" and other reserved IDs that validate_run_id rejects, so a reserved run_id could create a run directory that collides with CURRENT_RUN_FILENAME or bypass reserved-name rules.
- **Proposed resolution**: Mirror step 4: bind safe_run_id = validate_run_id(run_id) before _open_or_create_subdir(clone_dir_fd, safe_run_id) and keep False on ValueError.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_progress_statusline.py:148-173,325-349
- **Concern**: Post-fd swap tests are conflated with symlink-refusal expectations. Scenario: The plan replaces swap tests with post-fd-acquisition swaps but also lists test_activate_run_refuses_clone_dir_swap_before_write under symlink-refusal broadening. Current swap tests hook assert_no_symlink and expect OSError or False. After fd pinning, swap after fd acquisition should succeed via the held fd into the renamed original directory, not refuse. Mis-specified tests can pass while writes never reach the pinned dir or force incorrect refusal semantics.
- **Proposed resolution**: Rename/reframe post-fd swap tests as success cases: after rename-plus-symlink at the original path, assert activate_run succeeds and current lands in the renamed clone dir (not the outside target); assert append_breadcrumb_for_run returns True and the log lands in the renamed run dir. Reserve broadened OSError matching for pre-open symlink fixtures like test_activate_run_refuses_symlinked_run_dir_and_current only. ## Findings ### 1. [correctness] `python/larch/report/progress_file.py:326-343` — Explicit `validate_run_id` missing from append rewrite Step 4 requires `validate_run_id` once in `activate_run`. Step 5 rewrites `append_breadcrumb_for_run` to use `_open_or_create_subdir(clone_dir_fd, run_id)` but never calls `validate_run_id`. Today validation happens indirectly via `run_progress_dir()`. `_validate_dir_entry_name` only rejects `.`, `..`, and slashes. It accepts `"current"`, which `validate_run_id` reserves for the active-run pointer. Without the explicit call, a reserved run ID could create a run directory that conflicts with `CURRENT_RUN_FILENAME`. **Suggested revision:** Add `safe_run_id = validate_run_id(run_id)` before `_open_or_create_subdir`, matching step 4. ### 2. [correctness] `python/tests/report/test_progress_statusline.py:148-173,325-349` — Post-fd swap tests must expect success, not refusal The plan’s edge case requires that a path swap after fd acquisition must not redirect writes outside the pinned directory. That implies writes continue through the held fd into the renamed original directory. The test plan replaces swap tests with post-fd-acquisition swaps, but it also lists `test_activate_run_refuses_clone_dir_swap_before_write` under symlink-refusal broadening. Current tests hook `assert_no_symlink_path_or_ancestors` and expect `OSError` or `False`. That matches check-then-open TOCTOU, not fd-pinned behavior. After fd acquisition, `activate_run` should succeed and write `current` into the renamed clone dir. `append_breadcrumb_for_run` should return `True` and write into the renamed run dir. Negative-only checks (`assert not (target / ...).exists()`) do not prove the pinned write succeeded. **Suggested revision:** Reframe post-fd swap tests as success cases with positive assertions on the renamed real directories. Keep broadened `OSError` matching only for pre-existing symlink fixtures such as `test_activate_run_refuses_symlinked_run_dir_and_current`.



### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_file.py:326-333
- **Concern**: append_breadcrumb_for_run rewrite does not explicitly preserve run_id validation before fd-relative subdir creation. Scenario: _open_or_create_subdir only calls _validate_dir_entry_name, which allows values validate_run_id rejects such as current or names with spaces. If the rewrite passes raw run_id, invalid calls can create/write run dirs and return True instead of preserving best-effort False.
- **Proposed resolution**: Add a firm step to call safe_run_id = validate_run_id(run_id) inside the try before _ensure_directory_fd, then pass safe_run_id to _open_or_create_subdir and keep ValueError in the false-return catch.



