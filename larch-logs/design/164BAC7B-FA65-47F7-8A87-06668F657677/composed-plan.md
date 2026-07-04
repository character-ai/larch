## Plan

## Approach

Two-part fix. The root cause is `_rebase_under_tmpdir` in `run_log_batch.py`. The defense-in-depth fix is `write_tally_main` in `voting.py`.

**Root cause (`run_log_batch._rebase_under_tmpdir`)**: when `run-log write` receives an absolute `--input-file` path that is not under `IMPLEMENT_TMPDIR`, line 115 strips the leading `/` and rebases the path under `IMPLEMENT_TMPDIR`. For example, a temp file at `/var/folders/.../T/write-tally-record.xxx` becomes `IMPLEMENT_TMPDIR/var/folders/.../T/write-tally-record.xxx`, which does not exist. `_redact_to_temp` then raises ENOENT. Fix: return the absolute path as-is when it is not under `IMPLEMENT_TMPDIR`.

**Defense-in-depth (`voting.write_tally_main`)**: pass `dir=Path(args.log_root).parent` to `NamedTemporaryFile` so the temp record stages under the implement session root instead of ambient `$TMPDIR`. Both callers pass `--log-root <impl_tmpdir>/larch-logs`, so the parent is always `impl_tmpdir`. This makes the temp path already under `IMPLEMENT_TMPDIR`, so `_rebase_under_tmpdir` succeeds even without the root-cause fix, and guards against a broken system `$TMPDIR` from any other source.

## Files to modify/create

### UPDATED: python/larch/report/run_log_batch.py

Fix `_rebase_under_tmpdir` at line 115. In the `except ValueError` branch, return `candidate` instead of `tmpdir / Path(*candidate.parts[1:])`.

Before:
```python
except ValueError:
    return tmpdir / Path(*candidate.parts[1:])
```

After:
    return candidate

Keep all other branches unchanged. The function's only invariant violation is this one arm, which incorrectly rebases absolute paths that are not under `IMPLEMENT_TMPDIR`.

Note: `_resolve_log_root` has the same rebasing pattern at line 258 for `--log-root` paths; that behavior is intentional (session-relative log roots) and is NOT changed.

### UPDATED: python/larch/review/voting.py

Change the `NamedTemporaryFile` call in `write_tally_main` at line 1466 to add `dir=Path(args.log_root).parent`.

with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, prefix="write-tally-record.") as handle:

with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, prefix="write-tally-record.", dir=Path(args.log_root).parent) as handle:

Keep the rest of the flow unchanged: validate arguments, compose the record, write temp, call `run-log write`, unlink in `finally`, re-emit stdout KV lines.

### UPDATED: python/tests/report/test_run_logs.py

Two changes:

**1. Update existing test** `test_larch_log_write_rebases_root_relative_log_root_and_input_file` (line 1506): change the `--input-file` argument from `/token-report.json` to `str(source)` (the actual absolute path of the source file created at line 1513). This preserves the assertion that `--log-root /larch-logs` is correctly rebased under IMPLEMENT_TMPDIR while no longer relying on `--input-file` rebasing for absolute paths outside IMPLEMENT_TMPDIR.

**2. Add unit tests** for `_rebase_under_tmpdir`. Import via `from larch.report.run_log_batch import _rebase_under_tmpdir`.

Test cases with `IMPLEMENT_TMPDIR=str(tmp_path)`:
- Absolute path already under `IMPLEMENT_TMPDIR`: returns unchanged.
- Absolute path NOT under `IMPLEMENT_TMPDIR` (e.g., `/var/folders/.../T/foo`): returns the path unchanged (the fix; was previously rebased).
- Relative path: prepended with `IMPLEMENT_TMPDIR`.
- Empty path with `default_leaf`: returns `IMPLEMENT_TMPDIR / default_leaf`.
- No `IMPLEMENT_TMPDIR` set: returns the path unchanged.

### UPDATED: python/tests/review/test_voting.py

Add a regression test near the existing `write-tally` tests.

Test shape:
- Set `IMPLEMENT_TMPDIR` to `str(tmp_path)` via `monkeypatch.setenv`.
- Set `TMPDIR` to a malformed nonexistent path (e.g., `str(tmp_path / "fake" / "var" / "folders" / "T")`) via `monkeypatch.setenv`.
- Pass `--log-root str(tmp_path / "larch-logs")` so `Path(args.log_root).parent == tmp_path == IMPLEMENT_TMPDIR`.
- Invoke `voting write-tally` through `run_cli`.
- Assert return code `0`.
- Assert `tmp_path / "larch-logs" / "implement" / run_id / "code-review-tally.json"` exists and has `batch == "code-review-tally"`.
- Assert no file was created under the malformed `TMPDIR` path.

This test is red on the unfixed code and green after both fixes.

## Edge cases

- `--log-root` parent must exist when `write_tally_main` is called. In current callers it always does. The `NamedTemporaryFile` will raise ENOENT if it does not, which surfaces loudly.
- A relative `--log-root` stages the temp record under its relative parent. No known callers pass relative paths.
- The `_rebase_under_tmpdir` fix makes it a pass-through for non-local absolute paths. Any absolute path under `IMPLEMENT_TMPDIR` is still returned as-is (the `relative_to` branch succeeds).
- The `test_larch_log_write_rebases_root_relative_log_root_and_input_file` assertion on `--log-root /larch-logs` rebasing is unaffected; only the `--input-file` arm changes.

## Failure modes

- If `Path(args.log_root).parent` is wrong for a future caller, `write_tally_main` fails before `run-log write`. The failure is visible through the existing nonzero return and sidecar path.
- A future caller passing a deliberately pseudo-absolute `--input-file` (for rebasing) will no longer get that rebase. No existing caller in the codebase passes input files this way except the now-updated test.

## Testing strategy

Run targeted tests after implementing:

- `python3 -m pytest python/tests/report/test_run_logs.py -k "rebase_under_tmpdir or rebases_root_relative"`
- `python3 -m pytest python/tests/review/test_voting.py -k write_tally`

Also verify locally: set `TMPDIR` to a nonexistent nested path and `IMPLEMENT_TMPDIR` to a real directory, run `python3 python/cli.py voting write-tally ...`, confirm `code-review-tally.json` lands.

## Acceptance

Run targeted tests after implementing:

- `python3 -m pytest python/tests/report/test_run_logs.py -k "rebase_under_tmpdir or rebases_root_relative"`
- `python3 -m pytest python/tests/review/test_voting.py -k write_tally`

Also verify locally: set `TMPDIR` to a nonexistent nested path and `IMPLEMENT_TMPDIR` to a real directory, run `python3 python/cli.py voting write-tally ...`, confirm `code-review-tally.json` lands.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 55
