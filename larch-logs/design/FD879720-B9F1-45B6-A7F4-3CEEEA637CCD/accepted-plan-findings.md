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

