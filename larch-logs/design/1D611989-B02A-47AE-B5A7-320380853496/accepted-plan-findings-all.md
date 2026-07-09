### FINDING_3: Default-append symlink/TOCTOU test needs migration
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Progress Symlink Safety
- **Severity**: major
- **Concern**: The plan still leaves the old `test_append_breadcrumb_rechecks_after_mkdir` / flat-path symlink-recheck coverage pointed at `progress_path`, but the new default append path is run-scoped and fd-anchored. Without activating a run and retargeting the test, it will either fail before the new guard runs or pass vacuously without exercising the intended TOCTOU check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add to test updates: retarget this test to an fd-layer swap (like test_append_breadcrumb_for_run_pins_run_dir_after_fd_acquisition) or replace it with default-append symlink/current pinning coverage.
  - From Codex-Arch: Activate a real run before the append test, and for the statusline case point `current` at the active run and build the symlinked ancestor around `run_progress_path(...)` so the guarded path is actually exercised.
  - From Cursor-Pragmatic: Add this test to the plan: call activate_run before append, assert against run_progress_path instead of progress_path, and retarget the monkeypatched assert_no_symlink_path_or_ancestors hook to the run-scoped fd open path
  - From Codex-Pragmatic: Activate a run in the fixture before calling append_breadcrumb, then keep the mocked second assert_no_symlink_path_or_ancestors failure to verify the fd-safe recheck path
  - From Cursor-Requirements: Replace or delete this test in the plan: either add a default-append fd-pinning case mirroring test_append_breadcrumb_for_run_pins_run_dir_after_fd_acquisition (activate run, swap run dir after fd acquisition, assert append_breadcrumb returns False and outside target is untouched) or explicitly retire the test as flat-log-only coverage
  - From Codex-Requirements: Rework or remove the old default-append symlink recheck test. Scenario: The new run-scoped append path no longer performs the two path-based symlink checks this test counts on, so it will fail before verifying the new flow and block the targeted pytest run.
  - From Cursor-dyn-Progress Symlink Safety: Update or replace this test in the test file section: either drop it or rewrite it to assert fd-anchored behavior (e.g. reuse the pin-after-fd pattern from test_append_breadcrumb_for_run_pins_run_dir_after_fd_acquisition) on default append_breadcrumb after activate_run


### FINDING_4: Statusline must avoid private cross-module read
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The new statusline helper calls a private `progress_file` reader from another runtime module, which will trigger Ruff and pyright unless the code is wrapped or suppressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Either expose a public active-run reader in `progress_file.py` or annotate the new call site with `# noqa: SLF001` and `# pyright: ignore[reportPrivateUsage]`.


### FINDING_5: Statusline current lookup needs fd-safe read
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-Progress Symlink Safety
- **Severity**: major
- **Concern**: The planned statusline path still resolves `current` through a path-based read, so a swapped symlink ancestor or file can race between the check and open and let `render_statusline` consume the wrong run's breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Open the clone directory with the fd-safe helper and read current through _read_active_run_id_from_dirfd, or add an ancestor symlink check before reading current.
  - From Codex-dyn-Progress Symlink Safety: Read current from a verified clone dir fd with progress_file._read_active_run_id_from_dirfd, or add a dirfd-based helper and use that in render_statusline before constructing run_progress_path


### FINDING_3: Statusline symlink test needs to exercise the active-run pointer path
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The current symlink-safety test still uses a flat progress log and never sets an active `current`, so it does not cover the new active-run reader path. That lets a regression in the symlink-safe pointer lookup slip through even though the test appears to cover the feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Retarget the test to activate a run and place the symlink on the active-run `current` or run-log ancestor chain, then assert `render_statusline` still returns `""`.`


### FINDING_4: Statusline reader still needs a directory-open path that is fd-relative, not path-based
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The proposed `read_active_run_id` flow still opens the clone directory by path after checking ancestors. That leaves a time-of-check/time-of-use gap where a symlink swap can redirect the statusline reader to another tree’s `current` and breadcrumbs, so the fd-safe lookup fix is still incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: `Add a no-create fd-relative opener for existing clone dirs, mirroring `_ensure_directory_fd` traversal without mkdir, and use it in `read_active_run_id`; return `None` on missing components.`


