## Goal
Implement issue #4976: [IMPLEMENTING] [py-code-quality] Fix atomicity and broad-suppression safety bugs in state subsystem.

## Implementation Plan
## Plan

### Approach

Use the existing shared `larch_io.atomic_write`.

Keep scope to the approved surfaces:

- `python/run_logs.py`
- `python/tokens.py`
- `python/test_run_logs.py`
- `python/test_tokens.py`

Do not touch:

- other `larch_io.atomic_write` callers
- non-state `suppress(Exception)` sites
- secret-scrub fail-closed behavior
- symlink-escape guards
- `python/review_and_fix.py`

Surface failures via stderr warnings without changing caller exit semantics where the current code already continues or returns `0`.

Preserve existing error contracts at public and commit boundaries:

- `_copy_tree_to_repo` signals publish failures through the fourth tuple element (`scrub_error`), consumed by `_commit_run` at `run_logs.py:1878-1879`.
- `publish_breadcrumbs_main` is a CLI entry that prints refusal lines to stderr and returns `1` or `2`; it does not raise.
- Reserve `ValueError` only inside `_replace_tree_with_backup` for internal invariant violations; callers convert at boundaries before errors reach `larch_log_commit_main`, `flush_logs_pre`, or the publish-breadcrumbs CLI.

## Files to modify/create

### UPDATED: `python/run_logs.py`

- Change `_atomic_write()` to call `larch_io.atomic_write(..., nofollow=True)`.
- Add a small private helper for tree publish replacement: `_replace_tree_with_backup(staged: Path, dest: Path) -> None`.
  - Before moving anything, refuse `dest.is_symlink()` and any existing non-directory `dest` (raise `ValueError` with a clear message). Only replace an existing directory; missing `dest` is fine.
  - Derive backup name as `dest.parent / f".{dest.name}.removing"`.
  - If backup exists and `dest` also exists (as a directory): backup is stale from a prior incomplete cleanup; remove only the backup path.
  - If backup exists and `dest` is missing: backup is the only committed copy (interrupted previous publish); rename backup to `dest` first, then fall through to the normal replace path.
  - Rename `dest` to backup (atomic).
  - Rename `staged` to `dest` (atomic). On failure, best-effort restore backup to `dest` and re-raise.
  - Remove backup after successful publish.
- Use that helper in `_copy_tree_to_repo()` with an explicit gate before any rename:
  - If `dest.is_symlink()` or (`dest.exists()` and not `dest.is_dir()`): return `([], dest, scrub_violations, "<clear refusal message>")` via the existing `scrub_error` tuple slot. Do not raise `ValueError` and do not call `tmp_dest.replace(dest)`.
  - Elif `dest.exists()` and `dest.is_dir()` and not `dest.is_symlink()`: call `_replace_tree_with_backup(tmp_dest, dest)` instead of `shutil.rmtree(dest)` + `tmp_dest.replace(dest)`. On `ValueError` from the helper, return the message in `scrub_error`.
  - Elif not `dest.exists()` and the backup path `dest.parent / f".{dest.name}.removing"` exists: call `_replace_tree_with_backup(tmp_dest, dest)` so the interrupted publish restores the only committed copy before publishing the staged tree. On `ValueError`, return the message in `scrub_error`.
  - Else (`dest` missing and no backup): call `tmp_dest.replace(dest)` only.
- Use that helper in `publish_breadcrumbs_main()` with the same explicit refuse-before-replace gate, matching the CLI int-return contract:
  - If `dest.is_symlink()` or (`dest.exists()` and not `dest.is_dir()`): print a refusal line to stderr and return `1`. Do not raise or call `staged.replace(dest)`.
  - Elif `dest.exists()` and `dest.is_dir()` and not `dest.is_symlink()`: call `_replace_tree_with_backup(staged, dest)` instead of `shutil.rmtree(dest)` + `staged.replace(dest)`. On `ValueError`, print the message to stderr and return `1`.
  - Elif not `dest.exists()` and the backup path exists: call `_replace_tree_with_backup(staged, dest)` instead of `staged.replace(dest)` directly. On `ValueError`, print to stderr and return `1`.
  - Else (`dest` missing and no backup): call `staged.replace(dest)` only.
- Keep the existing `_publish_run_tree_to_repo()` backup flow unless reuse of the new helper is a small cleanup with no behavior change.
- Replace the three scoped broad suppressions:
  - manifest update in `_commit_run`
  - breadcrumb publish in `_commit_run`
  - full flush in `larch_log_flush_main`
- For each suppression site, catch narrow expected exceptions and print a warning to `sys.stderr`.
  - Manifest update: catch `OSError`, `json.JSONDecodeError`, `TypeError`, `ValueError`, `UnicodeError`.
  - Breadcrumb publish: catch `OSError`, `ValueError`, `ShipError`, `UnicodeError`.
  - Full flush: structure as a try/except ladder:
    - First handlers: catch `OSError`, `ValueError`, `ShipError`, `UnicodeError`; print `WARN: larch-log flush failed: {exc}` and `return 0`.
    - After `_commit_run(...)`, inspect `result.returncode`. On non-zero, print warning and continue.
    - Final safety net: `except Exception as exc:` prints `WARN: larch-log flush failed: {exc}` and `return 0`.
- After `publish_breadcrumbs_main(...)` returns inside `_commit_run`, inspect the return code. On non-zero, print a stderr warning naming the operation and including the rc.
- Warning text should name the operation and include the exception or failure detail.
  - Example shapes:
    - `WARN: larch-log commit manifest update failed: {exc}`
    - `WARN: larch-log commit breadcrumb publish failed: rc={rc}`
    - `WARN: larch-log flush failed: {exc}`

### UPDATED: `python/tokens.py`

- Change `_atomic_text()` to call `larch_io.atomic_write(..., nofollow=True)`.
- Preserve existing prefix and newline behavior:
  - `prefix=f".{path.name}."`
  - `newline="\n"`

### UPDATED: `python/test_run_logs.py`

Add focused coverage:

- `_atomic_write()` rejects a symlink destination (or monkeypatch to assert `nofollow=True`).
- `_replace_tree_with_backup()` refuses symlink `dest` and non-directory `dest` with `ValueError`.
- `_copy_tree_to_repo()` does not call `shutil.rmtree(dest)` when replacing an existing committed run tree (monkeypatch `shutil.rmtree` to fail on live dest; allow cleanup of backup path).
- `_copy_tree_to_repo()` interrupted-publish recovery: when `dest` is missing but backup exists, assert backup is restored and staged tree publishes.
- `publish_breadcrumbs_main()` does not call `shutil.rmtree(dest)` when replacing an existing breadcrumbs tree.
- Warning-on-swallow: monkeypatch `_update_manifest_v2` to raise `OSError`; assert `_commit_run()` continues and writes warning to stderr.
- Warning-on-swallow: monkeypatch `publish_breadcrumbs_main` to return `1`; assert `_commit_run()` continues and writes warning to stderr.
- Warning-on-swallow: monkeypatch `_stage_pre_commit` to raise `OSError`; assert `larch_log_flush_main()` returns `0` and writes warning to stderr.

### UPDATED: `python/test_tokens.py`

- `_atomic_text()` rejects a symlink destination (or monkeypatch to assert `nofollow=True`).

## Edge cases

- If a stale backup exists before publish, remove only the backup path.
- Never remove the live destination before the staged replacement is ready.
- If the staged replacement fails after moving the live destination to backup, restore the backup when possible.
- If backup cleanup fails after publish, let the exception surface.
- Preserve existing behavior when the source and destination resolve to the same tree.
- Preserve breadcrumb symlink, hardlink, redaction, and confinement guards.

## Failure modes

- A failed manifest update during commit should no longer disappear silently.
- A failed breadcrumb publish during commit should no longer disappear silently.
- A failed full flush should no longer disappear silently.
- A crash between old-tree backup and new-tree publish may leave a backup tree, but should not destroy the only committed copy.

## Testing strategy

Run:

- `make py-test`
- `make py-lint`
- `make lint`

For faster local iteration first, run:

- `python3 -m pytest python/test_larch_io.py python/test_run_logs.py python/test_tokens.py`

## Notes

- The shared `larch_io.atomic_write` dependency (#4975) has already landed.
- Do not add `exclusive=True` or `mode=0o600` to `run_logs._atomic_write` or `tokens._atomic_text`; the approved scope only requires `nofollow=True`.
- Do not update `SECURITY.md`; this change hardens existing behavior without changing the documented security contract.

## Acceptance

One hardened atomic-write (`nofollow=True`) used by all state writers in scope; no rmtree-before-rename in either publish path; broad suppressions around state IO narrowed and logged; parity/units green.

diff_lines: 272

## Test plan
(no test plan section in plan-file)
