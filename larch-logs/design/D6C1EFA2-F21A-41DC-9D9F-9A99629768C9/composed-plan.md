## Plan

## Approach

Use the minimum fix for the reported selection bug.

- Keep discovery scoped to live pointer files for the same canonical repo.
- Change implement candidate freshness from tmpdir directory mtime to pointer file mtime.
- Leave design discovery unchanged, since it already uses pointer mtime.
- Do not add session-start marker files or stale-age thresholds in this change.
- Do not change teardown unless tests reveal an existing clear-pointer path is broken. `skills/implement/scripts/step-18.sh` already calls `session clear-implement-pointer`.

## Files to modify/create

### UPDATED: python/progress_report.py

Change `_implement_candidate` so the returned `LiveRun.mtime` uses `_path_mtime(pointer)`.

Current behavior:

- A tmpdir root write from an older session can make that older session win.
- Step 5 nested writes do not reliably refresh the active tmpdir root.

New behavior:

- The newest implement pointer for the matching repo wins.
- Implement and design candidates use the same freshness semantic.

Keep `_discover_live_run` aggregation simple.

### UPDATED: python/test_progress_report.py

Update the tests that encode the old tmpdir-mtime contract.

- Rename or rewrite `test_newest_implement_tmpdir_wins`.
- Assert the newest implement pointer wins even when its tmpdir directory mtime is older.
- Replace or rewrite `test_stale_pointer_newer_file_active_tmpdir_wins`, since that currently protects the old behavior.
- Add a direct regression for the bug:
  - Same repo.
  - Old failed tmpdir has a newer directory mtime and a `copy-plan.stderr.log`.
  - Active session pointer has a newer pointer mtime.
  - Active tmpdir has an older directory mtime.
  - Active timing mark is `Step 5 — code review`.
  - Assert the report comes from the active session.
- Use a monkeypatched `_render_step5` if needed so the test isolates discovery selection from Step 5 rendering details.

## Edge cases

- **Dangling implement pointers:** Keep current skip behavior. `_implement_candidate` already ignores missing tmpdirs.
- **Repo symlinks:** Keep canonical cwd comparison unchanged.
- **Design sessions:** No behavior change. They already rank by pointer mtime.
- **Equal mtimes:** Do not add tie-break logic unless a test needs it. Equal mtimes are not the reported failure mode.

## Failure modes

- If a stale pointer has a newer mtime than the active pointer, this fix can still select stale state.
- That is a separate lifecycle hygiene issue.
- Do not add age thresholds in this fix, because they can hide valid long runs.
- Do not delete tmpdirs or pointers from the progress hook path. The hook must remain read-only and fail-open.

## Testing strategy

Run targeted Python tests first:

- `python3 -m pytest python/test_progress_report.py`

Then run required repository checks:

- `make py-lint`
- `make py-test`
- `make lint`

No Bash fence changes are planned.

## Acceptance

Plan accepted at Gate C (panel degraded — 4/8 reviewer slots produced output).

diff_lines: 34
