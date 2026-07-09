### FINDING_1: Cleanup should age run dirs from `breadcrumbs.log`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `cleanup_old_progress_files` needs a run-scoped age signal. Using the parent run directory mtime is unstable because appending to `breadcrumbs.log` does not necessarily refresh the directory timestamp, so an active run can look old and be deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When deciding whether a run-id subdirectory is aged out, read mtime from run_progress_path(...)/breadcrumbs.log when that regular file exists; otherwise fall back to the run directory mtime. Keep only the cutoff timestamp in the shared helper. Add a cleanup test that touches an old run-dir mtime but a fresh breadcrumbs.log mtime and asserts the directory is preserved.
  - From Cursor-Innovation: Specify: use breadcrumbs.log mtime when the file exists, else the run-directory mtime; apply the shared cutoff helper to that value; test aged vs fresh run dirs using log mtime.
  - From Cursor-Pragmatic: When reaping run-id directories, compute age from run_progress_path(...)/breadcrumbs.log mtime when that regular file exists; fall back to the directory mtime only when the log is absent. Add a test that appends refresh retention for an explicit run dir without a current pointer.
  - From Cursor-Requirements: Define run-dir age from run_progress_path(...)/breadcrumbs.log mtime when the log exists, otherwise the directory mtime; share the same cutoff helper as flat *.log cleanup


### FINDING_2: `activate_run` still has a parent-swap race
- **Reviewer(s)**: Codex-Arch, Cursor-dyn-Progress Security, Codex-dyn-Progress Security
- **Severity**: major
- **Concern**: `activate_run` can still lose the atomic-pointer safety guarantee if the clone directory is swapped after the last ancestry check but before the temp-file write/replace sequence. That can redirect `current` outside the validated tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Create the clone dir and run dir first, then call `larch_io.atomic_write(..., create_parent=False, nofollow=True, mode=0o600, prefix=".current.")` after the last symlink check.
  - From Cursor-dyn-Progress Security: Call `assert_no_symlink_path_or_ancestors(current_run_path(...))` immediately before `atomic_write`, pass `create_parent=False`, and keep raising on failure
  - From Codex-dyn-Progress Security: Add a final ancestor check immediately before the atomic_write call and force create_parent=False after the verified mkdirs, or move temp creation to a verified directory handle


### FINDING_3: Cleanup must spare the active run directory named by `current`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-Progress Security
- **Severity**: major
- **Concern**: The cleanup sweep only exempts the `current` pointer file, not the run directory that pointer names. That lets an aged but still-active run tree be pruned while it is in use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: The sweep can delete an aged but still-active run dir because the plan only exempts the `current` file itself, not the run directory it names.
  - From Cursor-Innovation: Add: read and validate current inside each clone dir; never remove that run-id subdirectory even when its mtime is past cutoff; add a test that an aged but active run dir survives cleanup.
  - From Codex-Innovation: Cleanup only skips the current pointer file, not the run directory named by that pointer.. Scenario: An aged run that is still active can be pruned, deleting the live breadcrumb log while the run is in progress.
  - From Cursor-Pragmatic: Cleanup must skip the run directory named by current, not just avoid deleting the pointer file. Scenario: The cleanup bullet skip active current pointer files is ambiguous. A literal reading only protects the pointer file, while long-lived activated runs can have old directory mtimes and still be active. cleanup can remove the live run tree.
  - From Cursor-Requirements: Cleanup does not protect the active run directory named by `current`. Scenario: Retention only skips deleting the `current` pointer file; an aged sibling run directory can still be removed while `current` still points at it, breaking the per-clone active-run contract later pieces will rely on
  - From Codex-Requirements: The cleanup design skips the `current` pointer file, but it never says to exempt the run directory named by that pointer.. Scenario: A live run whose breadcrumbs directory ages past the retention cutoff can be deleted mid-session, which drops active breadcrumbs and can blank the statusline.
  - From Codex-dyn-Progress Security: Skip the run ID named by current, and compute age from breadcrumbs.log or another file that advances on append


### FINDING_5: `validate_run_id` must reserve `current`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Progress Security
- **Severity**: major
- **Concern**: The reserved pointer basename `current` is accepted as a run ID, which collides with the pointer file path and can break activation/layout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reject run_id equal to current (and document CURRENT_RUN_FILENAME as reserved) in validate_run_id; add one invalid-ID test.
  - From Cursor-Pragmatic: In validate_run_id, reject run_id equal to `CURRENT_RUN_FILENAME` (and document the reserved name). Add a test case for current.
  - From Cursor-Requirements: Reject run_id equal to `CURRENT_RUN_FILENAME` (`current`) in `validate_run_id`; add a focused invalid-ID test case
  - From Cursor-dyn-Progress Security: Reject run_id equal to `CURRENT_RUN_FILENAME` (`current`) in `validate_run_id`; add `test_progress_statusline.py` invalid-ID case


### FINDING_6: Explicit-run appends need symlink-ancestor checks
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The explicit-run append path only guards the final log file, not the run-directory ancestry. A symlinked run directory can redirect writes outside the intended progress tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the same assert_no_symlink_path_or_ancestors checks that append_breadcrumb uses, before and after parent creation, and fail closed on symlinked run-dir ancestors.


### FINDING_1: Normalize `current` before validating run IDs
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `_read_active_run_id` reads the pointer text too literally. Because `activate_run` writes a newline-terminated run ID, validating the raw file contents can fail on a normal pointer and cause cleanup to treat the active run as missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `In _read_active_run_id, read only the first line, strip trailing newline/whitespace, then call validate_run_id. Document that this matches activate_run output. Seed the active-run cleanup test via activate_run (or an equivalent newline-terminated pointer) so the reader contract is exercised.`
  - From Cursor-Innovation: `In _read_active_run_id, read the pointer best-effort, strip trailing \n/\r/whitespace, then call validate_run_id. Add a test that uses activate_run output and asserts cleanup keeps the named run dir when only its directory mtime is stale.`
  - From Cursor-Pragmatic: `Add an explicit contract step: read `current`, take the first line or strip trailing newline/whitespace, then call `validate_run_id`. Add a cleanup test that activates a run, ages the run-directory mtime, and confirms the named run dir survives retention.`
  - From Cursor-Requirements: `Read the first line (or full small file), strip trailing newline/whitespace, then call validate_run_id. Return `None` on empty, unreadable, symlinked, or invalid content.`


### FINDING_2: Anchor activation writes to a verified directory handle
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The `activate_run` write path still relies on a final path-based ancestry check before creating and replacing `current`. A clone-dir swap after that check can redirect temp-file creation or replace operations outside the verified progress tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `Bind the temp/open step to a verified directory FD or another helper that cannot re-resolve the parent path after the last check.`
  - From Codex-Innovation: `Create the temp file through an already-open clone-dir handle, or make the atomic writer accept a pinned directory FD instead of a bare path.`
  - From Codex-Pragmatic: `Make activation fd-anchored to the verified clone dir. Open the clone dir with `O_DIRECTORY|O_NOFOLLOW` after mkdir and recheck, create the temp file and replace `current` using dir-fd relative operations or an equivalent helper, and add a race test that swaps the clone dir between the final check and write.`
  - From Codex-Requirements: `Revise activate_run to anchor the current write to a verified clone-directory fd, or otherwise make temp creation and replace fd-relative to that directory. Add a swap test for the gap between the final check and write.`


### FINDING_3: Remove aged run directories recursively, not with a non-empty-dir primitive
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The cleanup design says to remove aged run-id directories, but it does not spell out recursive deletion or equivalent log unlinking. Since run directories contain `breadcrumbs.log`, a plain directory remove will fail and leave stale runs behind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `Spell out the removal step, either recursive delete or unlink the log before rmdir, and keep the symlink re-check right before deletion.`
  - From Cursor-Innovation: `Specify `shutil.rmtree` (after the final symlink re-check), matching `cleanup_skill._remove_entry`, inside the best-effort `except OSError: continue` loop. Add a test that an aged run dir with a log file is actually removed.`


### FINDING_4: Skip symlinked clone-directory roots during cleanup
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The clone-dir cleanup pass protects some children, but it does not explicitly reject symlinked clone-directory roots before descending. That leaves a path to follow a planted symlink and delete trees outside `progress_root`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Mirror `cleanup_skill._should_remove_by_age` / `_remove_entry`: skip any clone-dir candidate where `entry.is_symlink()` or `not entry.is_dir()`. Re-check `not run_dir.is_symlink()` immediately before removal. Add a test with a symlinked clone dir and assert nothing outside `progress_root` is deleted.`
  - From Codex-Innovation: `Skip symlinked clone dirs up front, and re-check the clone root immediately before enumerating or removing child run dirs.`
  - From Cursor-Requirements: `When enumerating clone-dir candidates (from `*.log` stems and from `progress_dir.iterdir()`), skip symlinked or non-directory roots, same as the flat-log pass.`


### FINDING_5: Pin the explicit-run append path before opening `breadcrumbs.log`
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The explicit-run `--run-id` append path still depends on path checks before opening the leaf log file. A swap in the parent chain can redirect the write even if the final component is protected with `O_NOFOLLOW`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Pin the run directory with an open handle and open `breadcrumbs.log` relative to it, or otherwise close the TOCTOU window around the write.`

