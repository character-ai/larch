## Proposed Design Outline

### Goals
- Make `write_tally_main` resilient to malformed or nonexistent `$TMPDIR` by staging the temp record under a known-good directory.
- Ensure `code-review-tally.json` lands in every live run regardless of ambient `$TMPDIR`.
- Add a regression test that reproduces the failure and verifies the fix.

### Non-goals
- Investigating or fixing the malformed `$TMPDIR` source in `bootstrap.py`/`session_env.py`.
- Backfilling missing `code-review-tally.json` for prior v52.2.4–v52.4.5 runs.
- Any changes to `CODE_REVIEW_LINE` in `final_report.py` (already cleaned up in #6169).

### Approach sketch
- In `write_tally_main` (`voting.py:1466`): add `dir=Path(args.log_root).parent` to the `NamedTemporaryFile` call so the temp record stages under the implement session root instead of ambient `$TMPDIR`.
- Both callers pass `--log-root impl_tmpdir/larch-logs`, so `Path(args.log_root).parent` is always `impl_tmpdir`, a guaranteed-existing directory.
- Add regression test: set `TMPDIR` to a nonexistent path, invoke `voting write-tally`, assert `code-review-tally.json` lands.

### Surfaces in scope
- `python/larch/review/voting.py` — `write_tally_main`, one-line change at line 1466.
- `python/tests/review/test_voting.py` — new regression test.

### Open questions
- None.
