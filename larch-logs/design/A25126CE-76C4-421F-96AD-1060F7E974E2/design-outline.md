## Proposed Design Outline

### Goals
- Bring `python/finalize.py` to full behavioral parity with bash `scripts/implement-finalize.sh` + `scripts/local-cleanup.sh` across postbump, postmerge, and teardown.
- Fix the two enumerated cross-file divergences: `ship.py` `_postmerge_should_flush` ctx timing and `ci_monitor.py` `stage_and_push` force-push gate.
- Add real (non-smoke) unit + bash-parity tests and a fail-closed gate so Python finalize cannot silently drift from bash.

### Non-goals
- Do not flip `LARCH_SHIP_PR_IMPL`; bash stays the shipped default (parity-only).
- Do not change bash behavior; `implement-finalize.sh` / `local-cleanup.sh` / `merge-pr.sh` are the untouched reference.
- No new `make test-merge-parity` target; the fail-closed gate lives in the pytest modules under `make py-test`.

### Approach sketch
- Audit each bash branch (postbump rebase -> force-push-gate; postmerge local-cleanup + verify-main; teardown rename A/B/C + manifest recovery + larch-log flush) and port missing behavior into `finalize.py`, reusing existing Python helpers (`rebase`, `run_logs`, `git`, `tracking_issue`).
- Bring postmerge cleanup to `local-cleanup.sh` parity: fetch + transient retry, orphan-flush reset, ahead-diagnostics, ff-only pull, branch delete; keep `verify-main` title check.
- Split postbump into separate rebase / remote-branch-check / force-push (lease) gate matching bash statuses; fix `_postmerge_should_flush` ctx and `stage_and_push` force-push.
- Rewrite `test_finalize_bash_parity.py` to actually invoke `scripts/implement-finalize.sh` via subprocess with PATH-stubbed `gh`/`git`, mirroring `test_merge_bash_parity.py`; `skipif` only when bash is genuinely absent.
- Add missing unit branches in `test_finalize.py` and an in-module guard so bash-present runs fail (not skip) when the parity suite would all-skip.

### Surfaces in scope
- `python/finalize.py`, `python/run_logs.py`, `python/ship.py`, `python/ci_monitor.py`
- `python/test_finalize.py`, `python/test_finalize_bash_parity.py`
- `Makefile` (stale shard-balance comment), `docs/linting.md` (doc refresh)
- Read-only reference: `scripts/implement-finalize.sh`, `scripts/local-cleanup.sh`, `scripts/merge-pr.sh`

### Open questions
- None blocking. Round 1 resolved cutover scope, audit depth, cross-file scope, and the parity-gate surface.
