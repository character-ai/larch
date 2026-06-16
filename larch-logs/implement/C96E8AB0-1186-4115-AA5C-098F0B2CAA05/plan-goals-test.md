## Goal
Implement issue #4464: [IMPLEMENTING] [BUG] (URGENT) Progress report seems to be broken in /implement review and ship-pr phases.

## Implementation Plan
## Plan

Context:
- `approach-synthesis.txt` is `NO_SKETCHES`.
- `discussion-round1.md` and `brainstorm.md` are absent.

Root cause: 591+ stale `current-implement-env-*.sh` pointer files accumulate because sessions interrupted before Step 18 never call `session clear-implement-pointer`. `_discover_live_run` selects the candidate with the highest pointer-file mtime. If a stale session's pointer was written more recently than the active session's pointer (e.g., a failed concurrent run started 1–4 minutes later), the stale tmpdir is selected. That stale tmpdir has only Step 0 artifacts, causing the progress report to display "Step 0 — preflight" instead of the actual current step.

Approach:
- Keep the fix narrow.
- Change only `/implement` live-run candidate ordering.
- Do not alter `/design` pointer selection.
- Do not garbage-collect stale pointer files.

### UPDATED: `python/progress_report.py`
- In `_implement_candidate`, set `LiveRun.mtime` from `_path_mtime(tmpdir)` instead of `_path_mtime(pointer)`.
- Leave `_design_candidate` unchanged.
- Keep the rest of `_discover_live_run` unchanged so it still compares candidates with `max(candidates, key=lambda run: run.mtime)`.

### UPDATED: `python/test_progress_report.py`
- Update `test_newest_pointer_wins` to reflect the new contract.
  - Rename it to `test_newest_implement_tmpdir_wins`.
  - Set pointer mtimes to the opposite order from tmpdir mtimes.
  - Assert the report comes from the implement tmpdir with the newer activity time.
- Add a regression test for the reported bug.
  - Create two valid implement pointers for the same repo.
  - Make the stale pointer file newer (higher pointer mtime).
  - Make the active tmpdir newer (higher tmpdir mtime).
  - Give the stale tmpdir a `Step 0 — preflight` mark.
  - Give the active tmpdir a `Step 5 — code review` mark and `round-1/panel-manifest.ndjson` so `_render_step5` returns a non-empty Step 5 report.
  - Assert `_report(str(cwd))` returns Step 5 content, not Step 0.
- Use `_set_mtime` on directories AFTER all file writes, to control directory mtime precisely.

Edge cases:
- Missing tmpdirs still return no candidate (existing `tmpdir.is_dir()` check).
- Pointer files with mismatched cwd are still filtered out.
- Design symlink pointer selection remains unchanged.
- Equal tmpdir mtimes may still tie by glob order; no tie-breaking needed.

Failure modes:
- If the test sets directory mtimes before writing child files, subsequent writes invalidate the intended ordering.
- If the regression test lacks `round-1/panel-manifest.ndjson`, `_render_step5` may return empty and fall back to generic.

Testing strategy:
- `python3 -m pytest python/test_progress_report.py`
- `make py-lint`
- `make py-test`
- `make lint`

## Acceptance

- Progress report shows the correct step (Step 5 code review or ship-pr phase) when multiple stale pointer files exist for the same repo.
- `test_newest_implement_tmpdir_wins` passes: tmpdir mtime wins over pointer mtime.
- Regression test `test_stale_pointer_newer_file_active_tmpdir_wins` passes: stale pointer with newer pointer-mtime but older tmpdir loses to active session with newer tmpdir.
- `make py-test` and `make lint` pass.

review_status: complete
rounds_completed: 1
diff_lines: 43

## Test plan
(no test plan section in plan-file)
