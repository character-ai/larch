### FINDING_1: Broaden symlink refusal match logic
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Fd Pinning Security
- **Severity**: major
- **Concern**: The kept symlink-refusal test still expects `match="symlink"`, but the fd-pinned open and destination checks now fail with helper-specific OSError text, so the test can fail even when refusal is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit test-task line: update that test to match fd-helper messages or errno, not symlink-only regex; keep refusal behavior, not the old assert wording
  - From Cursor-Pragmatic: In the test file section, require updating that test (or pytest.raises without a symlink-only match). Optionally add explicit symlink refusal messages in _open_or_create_subdir for parity.
  - From Cursor-Requirements: Add an explicit test-update step for this kept test: drop or broaden match="symlink" to the fd-pinned error messages (or assert OSError without a message regex) while still expecting refusal before any outside write
  - From Cursor-dyn-Fd Pinning Security: Add this test to the planned updates: relax `match` to the fd-helper errors or assert refusal via side effects only


### FINDING_3: Return a live directory fd from `_ensure_directory_fd`
- **Reviewer(s)**: Cursor-dyn-Fd Pinning Security
- **Severity**: major
- **Concern**: The implementation plan can accidentally keep `_ensure_directory`’s always-close cleanup in `_ensure_directory_fd`, which would hand callers a closed fd or double-close it after the fd is transferred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Fd Pinning Security: Step 1 must state `_ensure_directory_fd` returns the live final fd on success, closes only on failed traversal, and `_ensure_directory` alone closes in `finally`; cite the existing `finally` at 208-209 as the pattern to omit on success


### FINDING_2: Explicit validate_run_id is still needed before breadcrumb subdir creation
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The `append_breadcrumb_for_run()` rewrite appears to pass raw `run_id` into `_open_or_create_subdir()` without first calling `validate_run_id()`. `_validate_dir_entry_name()` is not equivalent: it does not preserve the reserved-name and other run-id checks that `validate_run_id()` enforces, so invalid or reserved IDs like `current` could create or collide with run directories instead of failing cleanly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `In Step 5, bind safe_run_id = validate_run_id(run_id) immediately after building the breadcrumb line and pass only safe_run_id to _open_or_create_subdir.`
  - From Cursor-Pragmatic: `Add an explicit step-5 bullet: call validate_run_id(run_id) (bind safe_run_id) before _open_or_create_subdir, matching step 4.`
  - From Cursor-Requirements: `Mirror step 4: bind safe_run_id = validate_run_id(run_id) before _open_or_create_subdir(clone_dir_fd, safe_run_id) and keep False on ValueError.`
  - From Codex-Requirements: `Add a firm step to call safe_run_id = validate_run_id(run_id) inside the try before _ensure_directory_fd, then pass safe_run_id to _open_or_create_subdir and keep ValueError in the false-return catch.`


