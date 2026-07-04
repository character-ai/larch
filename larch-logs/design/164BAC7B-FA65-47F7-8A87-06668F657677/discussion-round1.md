## Decision 1: Fix location for write_tally_main
- **Question**: Should the fix be at the `NamedTemporaryFile` call site in `write_tally_main`, at the `$TMPDIR` source in `bootstrap.py`/`session_env.py`, or both?
- **Resolution**: Fix at the call site. Pass `dir=Path(args.log_root).parent` to `NamedTemporaryFile` in `write_tally_main`. The `$TMPDIR` source is unconfirmed and fixing it would be a separate investigation. The call-site fix is isolated, testable, and immune to the TMPDIR origin question. Both callers (`flush_review_batches` and `write_self_review_tally`) route through the same `write_tally_main`, so one fix covers both.
- **Source**: codebase

## Decision 2: Which directory to use as the temp staging dir
- **Question**: What known-good directory should `NamedTemporaryFile(dir=...)` use?
- **Resolution**: `Path(args.log_root).parent` — i.e., the implement session root (`IMPLEMENT_TMPDIR`). This is guaranteed to exist at call time (callers set `--log-root` to `impl_tmpdir / "larch-logs"`, so the parent is `impl_tmpdir`). This avoids any dependency on the ambient `$TMPDIR`.
- **Source**: codebase

## Decision 3: Regression test scope
- **Question**: What regression test should be added?
- **Resolution**: Test that `write_tally_main` succeeds and writes `code-review-tally.json` even when `TMPDIR` is set to a nonexistent nested path. Add this to `python/tests/review/test_voting.py`, using `monkeypatch.setenv("TMPDIR", ...)` with a nonexistent path.
- **Source**: codebase (issue requirement)
