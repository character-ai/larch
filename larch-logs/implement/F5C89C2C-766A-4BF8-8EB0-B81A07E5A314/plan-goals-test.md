## Goal
Implement issue #5645: [IMPLEMENTING] [BUG] [ship-pr-ci] ship+CI breadcrumbs never committed (publish gate blocks staging).

## Implementation Plan
## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Follow the approved outline.
- Keep scope narrow:
  - Do not change `quiet_init`.
  - Do not change `PATH_QUIET_LOG_TEMPLATE`.
  - Do not update docs.
  - Do not create `<session-tmpdir>/breadcrumbs/` during bootstrap.
- Restore the documented contract: `breadcrumbs/` is a hint path only. Publishing derives the session root with `dirname` and scans for `larch-quiet-*.log`.

## Files to modify/create

### UPDATED: python/larch/report/run_logs.py

- In `_publish_breadcrumbs_with_warning`:
  - Keep `bread_src = log_root.parent / "breadcrumbs"`.
  - Replace the current combined guard with a `log_root.name` guard only.
  - Return early only when `log_root.name != "larch-logs"`.
  - Always call `publish_breadcrumbs_main` for valid larch log roots, even when `bread_src` does not exist.
- In `publish_breadcrumbs_main`:
  - Remove the `src.is_dir()` failure block.
  - Keep `source_root = src.parent`.
  - Keep `_breadcrumb_source_confined(source_root)` unchanged.
  - Keep the quiet-log scan, symlink guard, hardlink guard, redaction flow, and staged tree replacement unchanged.
- Preserve current no-op behavior:
  - Return `0` when the session root is outside active tmpdir env roots.
  - Return `0` when no matching quiet logs exist.
  - Do not create or replace `dest` when no quiet logs stage.

### UPDATED: python/test_run_logs.py

- Update `test_commit_run_warns_when_breadcrumb_publish_returns_nonzero`:
  - Remove the setup line that creates `log_root.parent / "breadcrumbs"`.
  - Optionally capture the argv passed to the monkeypatched `publish_breadcrumbs_main`.
  - Assert the warning still appears when the publisher returns nonzero.
  - This proves the outer publish path no longer requires a pre-created breadcrumbs directory.
- Add `test_commit_run_publishes_breadcrumbs_without_breadcrumbs_dir`:
  - Create a temporary repo and feature branch.
  - Create `log_root = tmp_path / "larch-logs"`.
  - Do not create `tmp_path / "breadcrumbs"`.
  - Create a run directory under `log_root / "implement" / "run-abc"` with at least one committed run artifact so `_copy_tree_to_repo` has rels to stage.
  - Write `tmp_path / "larch-quiet-ship.py-123.log"` with sample text.
  - Set `IMPLEMENT_TMPDIR` to `tmp_path`.
  - Clear other session tmpdir env vars that could affect confinement.
  - Call `_commit_run`.
  - Assert return code is `0`.
  - Assert `repo / "larch-logs" / "implement" / "run-abc" / "breadcrumbs" / "quiet.log"` exists.
  - Assert it includes the source header and sample breadcrumb text.
- Add `test_publish_breadcrumbs_main_succeeds_without_breadcrumbs_dir`:
  - Create `session = tmp_path / "session"`.
  - Do not create `session / "breadcrumbs"`.
  - Write `session / "larch-quiet-implement-1.log"`.
  - Set `IMPLEMENT_TMPDIR` to `session`.
  - Clear unrelated session tmpdir env vars.
  - Call `publish_breadcrumbs_main` with `--source-dir session/breadcrumbs`.
  - Assert return code is `0`.
  - Assert `dest / "breadcrumbs" / "quiet.log"` exists and contains the quiet-log text.
- Keep existing security tests intact:
  - Source outside session tmpdir still no-ops.
  - Source under session tmpdir still publishes.
  - Live tree replacement still avoids unsafe `rmtree` use.

## Edge cases

- Missing `source-dir` path should succeed if its parent is an active session tmpdir.
- Missing `source-dir` path outside active session tmpdirs should still no-op with return code `0`.
- No quiet logs should still leave the destination untouched.
- Symlink and hardlink quiet logs should still fail closed.
- Non-file matches should still be skipped.

## Failure modes

- If `log_root.name` is not `larch-logs`, breadcrumb publishing stays disabled.
- If tmpdir env vars are unset, `_breadcrumb_source_confined` currently returns `True`; do not change that behavior in this fix.
- If redaction or staged replacement fails, keep the existing warning and nonzero behavior.

## Testing strategy

- Run the focused test file:
  - `python3 -m pytest python/test_run_logs.py`
- If time is tight, run the focused tests first:
  - `python3 -m pytest python/test_run_logs.py -k 'breadcrumb or commit_run_warns_when_breadcrumb_publish_returns_nonzero'`
- No docs test is required because docs already describe the intended behavior.

## Acceptance

- Run the focused test file:
  - `python3 -m pytest python/test_run_logs.py`
- If time is tight, run the focused tests first:
  - `python3 -m pytest python/test_run_logs.py -k 'breadcrumb or commit_run_warns_when_breadcrumb_publish_returns_nonzero'`
- No docs test is required because docs already describe the intended behavior.

diff_added: 45
diff_deleted: 6
mechanical_churn: false
diff_lines: 51

## Test plan
(no test plan section in plan-file)
