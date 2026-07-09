## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Scope

Implement dormant run-scoped progress primitives only.

Use the provided `NO_SKETCHES` synthesis and direct repo inspection. Follow the approved outline and discussion constraints:

- Do not wire `/design` or `/implement` Step 0.
- Do not change `append_breadcrumb`, `progress_path`, writers, or `statusline.py` behavior.
- Do not update docs.
- Touch only the three in-scope files.

## Files to modify/create

### UPDATED: python/larch/report/progress_file.py

Add dormant helpers next to the existing flat-log code.

Planned helpers:

- `progress_clone_dir(repo_root) -> Path`
  - Return `progress_path(repo_root).with_suffix("")`.
  - This reuses the existing clone hash without changing `progress_path`.
- `current_run_path(repo_root) -> Path`
  - Return `<clone-dir>/current`.
- `run_progress_dir(repo_root, run_id) -> Path`
  - Validate `run_id`.
  - Return `<clone-dir>/<run-id>`.
- `run_progress_path(repo_root, run_id) -> Path`
  - Return `<clone-dir>/<run-id>/breadcrumbs.log`.
- `validate_run_id(run_id) -> str`
  - Accept only `[A-Za-z0-9._-]+`.
  - Reject empty values, `.`, `..`, `/`, `\`, path separators, control characters, and whitespace or tab.
  - Reject `run_id` equal to `CURRENT_RUN_FILENAME` (`current`); document that basename as reserved for the active-run pointer.

Add small private fd-anchoring helpers (module-local; do not change `larch_io.atomic_write`):

- `_open_verified_dir(path: Path) -> int`
  - Call `assert_no_symlink_path_or_ancestors(path)` first.
  - Open the directory with `os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW`.
  - Return the dir fd; caller closes it in `finally`.
- `_atomic_write_in_dir(dir_fd: int, name: str, text: str, *, mode: int = 0o600, temp_prefix: str = ".current.") -> None`
  - Create a temp file relative to `dir_fd` with `os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=dir_fd)`.
  - Write `text`, `fchmod` when needed, then `os.replace(temp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)`.
  - Refuse symlink temps or destination via `O_NOFOLLOW` and pre-replace `os.lstat(name, dir_fd=dir_fd)` checks.
  - Unlink the temp on failure.
- `_append_line_in_dir(dir_fd: int, name: str, line: str) -> None`
  - Open `name` relative to `dir_fd` with `O_WRONLY | O_APPEND | O_CREAT | O_NOFOLLOW`, mode `0o600`.
  - `fstat` and refuse non-regular files, then append via `os.fdopen`.
  - `chmod` best-effort to `0o600` after append.

- `activate_run(repo_root, run_id) -> None`
  - Validate the run ID.
  - Reject symlinked clone dir, run dir, pointer path, and ancestors with `assert_no_symlink_path_or_ancestors`.
  - Create the clone dir and run dir only after symlink checks.
  - Re-check symlink state after `mkdir`.
  - Open the verified clone directory with `_open_verified_dir(clone_dir)` and keep that fd through the write.
  - Write `<clone-dir>/current` through `_atomic_write_in_dir(dir_fd, CURRENT_RUN_FILENAME, f"{run_id}\n", mode=0o600, temp_prefix=".current.")` so temp creation and replace stay fd-relative to the already-verified clone directory.
  - Let invalid IDs and unsafe paths raise for loud CLI failure.
- `append_breadcrumb_for_run(repo_root, run_id, skill, step, text) -> bool`
  - Build the same breadcrumb line as `append_breadcrumb`.
  - Call `assert_no_symlink_path_or_ancestors` on the run log path before parent creation, `mkdir` the run dir, then re-check ancestors on the run log path after `mkdir`.
  - Open the verified run directory with `_open_verified_dir(run_dir)` and append through `_append_line_in_dir(run_dir_fd, RUN_BREADCRUMB_FILENAME, line)` so the leaf open is pinned to the verified run-dir fd instead of re-resolving the parent chain.
  - Do not read or write `current`.
  - Return `False` on best-effort failures, matching default append semantics.
  - Catch `OSError`, `TypeError`, and `ValueError`.

Add small private helpers for cleanup:

- `_cutoff_timestamp(retention_days, now)` — shared cutoff computation for flat logs and run dirs.
- `_entry_mtime_for_cleanup(entry_path, *, log_path: Path | None = None) -> float | None`
  - For run dirs, pass `log_path=run_progress_path(...)`.
  - When `log_path` exists as a regular non-symlink file, return that file's mtime.
  - Otherwise return the entry path's mtime.
- `_read_active_run_id(clone_dir) -> str | None`
  - Best-effort read of `<clone-dir>/current`.
  - Skip unreadable, symlinked, or missing pointer files.
  - Read only the first line (or the full small file), strip trailing `\n`, `\r`, and whitespace, then call `validate_run_id`.
  - Return `None` on empty, unreadable, symlinked, or invalid content.
  - Document that this normalization matches `activate_run` output.
- `_remove_run_dir(run_dir: Path) -> bool`
  - Re-check `not run_dir.is_symlink()` immediately before removal.
  - Remove the directory recursively with `shutil.rmtree(run_dir)` when it is a non-symlink directory, matching `cleanup_skill._remove_entry`.
  - Return `False` on `OSError`; callers treat removal as best-effort.

Extend `cleanup_old_progress_files`:

- Keep legacy flat `*.log` cleanup; compare each file's mtime against `_cutoff_timestamp`.
- Add a second pass over clone directories derived from existing flat-log hashes and any clone-hash directories already present under `progress_root`.
- When enumerating clone-dir candidates from `*.log` stems and `progress_dir.iterdir()`, skip symlinked or non-directory roots before descending, same as the flat-log pass.
- Re-check `not clone_dir.is_symlink()` and `clone_dir.is_dir()` immediately before enumerating child run dirs.
- For each clone dir:
  - Read the active run ID from `current` via `_read_active_run_id`.
  - Skip the `current` pointer file itself.
  - Never remove the run-id subdirectory named by the active pointer, even when that directory's mtime is past cutoff.
- For each other child run-id subdirectory:
  - Skip symlinks, non-directories, unreadable entries, malformed run IDs, and the reserved `current` name.
  - Decide age from `_entry_mtime_for_cleanup(run_dir, log_path=run_progress_path(...))`.
  - Remove the directory only when that age is below cutoff, using `_remove_run_dir(run_dir)` so `breadcrumbs.log` inside the run dir is deleted too.
- Treat cleanup as best-effort.
- Count each removed flat log or run directory as one removal.

Do not change `statusline.py`.

### UPDATED: python/larch/cli.py

Register the dormant CLI surface:

- Add `("progress", "activate"): ("larch.report.progress_file", "progress_activate_main")`.
- Keep `("progress", "note")` registered.
- Do not add `progress activate` to machine stdout unless the implementation emits parsed machine output. Prefer no stdout.

### UPDATED: python/tests/report/test_progress_statusline.py

Add focused tests while leaving existing flat progress and statusline tests unchanged.

New test coverage:

- Clone-dir, current pointer, and run-log helper paths.
- Valid run IDs such as `design-20260708.1`.
- Invalid run IDs:
  - empty
  - `.`
  - `..`
  - `current` (reserved pointer basename)
  - slash or backslash
  - control characters
  - whitespace or tab
- `activate_run`:
  - writes `current` atomically.
  - creates the run directory.
  - leaves a newline-terminated pointer value.
  - uses fd-anchored write via `_open_verified_dir` and `_atomic_write_in_dir`, either by direct assertion or monkeypatching those helpers.
  - refuses a clone-dir swap between the final ancestry check and write (race test that replaces the clone dir with a symlink after `mkdir` and before activation write).
- `_read_active_run_id`:
  - accepts newline-terminated pointer content written by `activate_run`.
  - returns `None` for malformed or whitespace-only pointer content.
- `progress note --run-id`:
  - appends to the explicit run log.
  - does not change `current`.
  - does not write the flat progress path.
- Explicit-run append symlink rejection:
  - symlinked run dir ancestors are refused before write.
  - symlinked run log is refused by explicit append.
  - refuses a parent-chain swap between final check and open by exercising the fd-anchored append path.
- `activate_run` symlink rejection:
  - symlinked run dir is refused.
  - symlinked `current` is refused.
- Cleanup:
  - removes aged run dirs, including dirs that still contain `breadcrumbs.log`.
  - preserves fresh run dirs.
  - preserves a run dir whose directory mtime is old but whose `breadcrumbs.log` mtime is fresh.
  - preserves the active run dir named by `current` even when only the directory mtime is stale; seed the pointer with `activate_run`, age the run-directory mtime, and confirm the named run dir survives retention.
  - removes aged legacy flat `*.log` files.
  - skips symlinked flat-log entries.
  - skips symlinked clone-directory roots and does not delete trees outside `progress_root`.

## Approach

1. Add constants in `progress_file.py`:
   - `CURRENT_RUN_FILENAME = "current"`
   - `RUN_BREADCRUMB_FILENAME = "breadcrumbs.log"`
   - a compiled run-id regex or a module-level pattern string.

2. Add `validate_run_id` first.
   - Keep it strict and small.
   - Raise `ValueError` for invalid IDs, including `current`.
   - Use it from every run-scoped helper and from `_read_active_run_id`.

3. Add path helpers.
   - Build on `progress_path(repo_root).with_suffix("")` so the old flat hash stays the source of truth.
   - Do not refactor `progress_path` unless unavoidable.

4. Add private fd-anchoring helpers.
   - Implement `_open_verified_dir`, `_atomic_write_in_dir`, and `_append_line_in_dir` in `progress_file.py` using Python 3.11 `dir_fd` APIs.
   - Keep writes confined to the three in-scope files; do not extend `larch_io.atomic_write` in this piece.

5. Add `activate_run`.
   - Validate the run ID before path construction.
   - Assert no symlink on pointer path, run dir, clone dir, and ancestors before `mkdir`.
   - Create clone dir and run dir with `mkdir(parents=True, exist_ok=True)`.
   - Assert again after `mkdir`.
   - Open the verified clone dir fd and write `current` through `_atomic_write_in_dir` so temp creation and replace cannot follow a swapped parent path.

6. Add explicit-run append.
   - Reuse `breadcrumb_line`.
   - Mirror the safe open pattern from `append_breadcrumb`, but pin the run directory with `_open_verified_dir` and append through `_append_line_in_dir`.
   - Keep the same before/after `mkdir` `assert_no_symlink_path_or_ancestors` checks on the run log path.
   - Catch `OSError`, `TypeError`, and `ValueError`.
   - Return `False`.

7. Update `progress_note_main`.
   - Add optional `--run-id`.
   - If set, call explicit-run append.
   - If absent, keep the existing flat append path.
   - Return `0` either way to preserve fail-silent note behavior.

8. Add `progress_activate_main`.
   - Parse `--repo-root` and required `--run-id`.
   - On parse error, return argparse exit code.
   - On invalid ID or unsafe path, print a concise error to stderr and return `2`.
   - On success, return `0`.

9. Extend cleanup.
   - Preserve current flat-log cleanup behavior with `_cutoff_timestamp`.
   - Add clone-dir and run-dir passes.
   - Skip symlinked or non-directory clone roots up front and re-check each clone root before enumerating children.
   - Read and honor the active run ID from `current` via normalized `_read_active_run_id`.
   - Age run dirs from `breadcrumbs.log` mtime when that regular file exists; otherwise use the run-directory mtime.
   - Skip active, fresh, symlinked, malformed, and unreadable entries.
   - Remove old run directories recursively with `_remove_run_dir` / `shutil.rmtree` inside the best-effort `except OSError: continue` loop.

## Edge cases

- Missing `current` pointer is not an error. This piece does not make readers follow it.
- Existing flat logs remain readable by current statusline code.
- Legacy flat logs are still cleaned by retention.
- Explicit-run append must not activate that run.
- Invalid run IDs, including `current`, must not create directories.
- A symlink swap between `mkdir` and write must fail closed; activation and explicit-run append close the TOCTOU window by keeping a verified dir fd through temp creation/open and replace/append.
- Cleanup must not follow symlinks or delete outside `progress_root`.
- Cleanup must not delete the run directory named by `current`, even when only the pointer file would otherwise be protected.
- Recent appends must keep a run dir alive even when the directory mtime is stale.
- Newline-terminated `current` content must still resolve the active run ID during cleanup.

## Failure modes

- A run ID with path traversal could write outside the cache. Strict validation blocks this.
- A run ID of `current` could collide with the pointer file. Reserved-name rejection blocks this.
- A symlinked pointer, run dir, or log could redirect writes. `assert_no_symlink_path_or_ancestors`, verified dir fds, `O_NOFOLLOW`, and fd-relative temp/replace on activation block this.
- A clone-dir swap after the final path check could redirect activation or explicit-run writes. Dir-fd-anchored helpers block this.
- Cleanup could delete the wrong tree if it follows symlinks, keys only on directory mtime, or uses non-recursive directory removal. Skip symlinked clone roots, honor normalized `current`, age from `breadcrumbs.log`, re-check before removal, and use recursive delete for aged run dirs.
- Reading `current` without stripping the trailing newline could drop active-run protection during cleanup. First-line normalization in `_read_active_run_id` blocks this.
- Accidentally changing `append_breadcrumb` or `statusline.py` would change live behavior too early. Keep those paths untouched and rely on existing tests.

## Testing strategy

Run focused checks:

- `python3 -m pytest python/tests/report/test_progress_statusline.py`
- `python3 -m ruff check python/larch/report/progress_file.py python/larch/cli.py python/tests/report/test_progress_statusline.py`
- `python3 -m pyright python/larch/report/progress_file.py python/larch/cli.py python/tests/report/test_progress_statusline.py`

If local tooling expects Make targets instead, use the repo's Python lint and test entry points, but keep the run scoped to these files where possible.

## Difficulty

MODERATE.

Rationale: this is dormant, bounded to three files, and avoids live workflow wiring. It still touches cleanup retention rules, active-run exemption, fd-anchored symlink-safe writes, and recursive run-dir removal, so the security and cleanup floor keeps it at least MODERATE. Confidence is high because the scope and non-goals are explicit.

difficulty: MODERATE
diff_added: 360
diff_deleted: 22
mechanical_churn: false
diff_lines: 382
