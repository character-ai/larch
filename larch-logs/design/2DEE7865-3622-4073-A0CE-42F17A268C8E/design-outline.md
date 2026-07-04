## Proposed Design Outline

### Goals
- Add a regression test for `capture_transcript_main` with `IMPLEMENT_TMPDIR` set.
- Confirm that a rendered transcript in system `$TMPDIR` is captured without path corruption.

### Non-goals
- Changing `_rebase_under_tmpdir` (already fixed by PR #6273).
- Fixing `_resolve_log_root` path-doubling (separate latent issue, out of scope).
- Adding `dir=IMPLEMENT_TMPDIR` call-site defense to `capture_transcript_main`.

### Approach sketch
- Add one test function near the existing `capture_transcript_main` tests (~line 2655 in `test_run_logs.py`).
- Set `IMPLEMENT_TMPDIR` via `monkeypatch.setenv` to a path outside system `$TMPDIR`.
- Mock `subprocess.run` to write JSON content to the renderer `--output` path.
- Assert `SESSION_TRANSCRIPT_STATUS=captured`.

### Surfaces in scope
- `python/tests/report/test_run_logs.py`

### Open questions
- None.
