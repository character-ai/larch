## Proposed Design Outline

### Goals
- Harden the ship pre-fix-rebase / phase14 paths: add missing guards, fix REBASE_COUNT tracking, add regression test.
- Deduplicate the step3 checks timeout (10800s) and commit-route marker timeout (15600s) to a single source of truth.
- Fix execution-issue artifact precedence so tmpdir markdown entries are not silently dropped when run-dir NDJSON also exists.
- Wire `test-write-final-report` into a CI shard and fix the SECURITY.md truncation-marker mismatch.

### Non-goals
- No restructuring of the ship.py state machine beyond the targeted guard additions.
- No changes to the CI runner, check engine, or final-report rendering beyond the artifact-precedence fix.
- No new public API surface beyond the one constant rename in `dispatch_leg.py`.

### Approach sketch
- In `dispatch_ship.py`: run branch/repo/in-progress-rebase checks before the phase14 flag skip; increment REBASE_COUNT after a successful rebase; write `.phase=rebase` state on the in-progress conflict path; write a pre-fix-rebase sentinel; add a monkeypatch test.
- In `dispatch_leg.py`: expose `_CHECKS_DEADLINE_MS` as a public constant.
- In `dispatch_commit_route.py`: derive both hardcoded timeouts (10800, 15600) from the named constants; update the existing test assertion for TIMEOUT_S.
- In `run-step-checks.sh`: derive TIMEOUT_S from a Python constant at startup to eliminate duplication.
- In `exec_issue_detail.py`: change `prefer_run_dir` semantics so tmpdir markdown takes precedence when non-empty, even if NDJSON exists; update the affected test.
- In `Makefile`: append `test-write-final-report` to one `test-harnesses-N` shard.
- In `SECURITY.md`: update the truncation-marker example text from the em-dash form to the colon form.

### Surfaces in scope
- `python/larch/implement/dispatch_ship.py`
- `python/larch/implement/dispatch_commit_route.py`
- `python/larch/implement/dispatch_leg.py`
- `skills/implement/scripts/run-step-checks.sh`
- `python/tests/implement/test_implement_dispatch.py`
- `python/larch/report/exec_issue_detail.py`
- `python/tests/report/test_exec_issue_detail.py`
- `Makefile`
- `SECURITY.md`

### Open questions
- None.
