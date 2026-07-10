## Proposed Design Outline

### Goals
- Let `/implement --merge` ship past client pre-commit fixer hooks that rewrite tracked `larch-logs/` files.
- Break the `step8-shippr` reship deadlock caused by the stale terminal `stalled` label.
- Keep committed run logs hook-clean by the client's own rules (no `--no-verify`).

### Non-goals
- No change to pre-terminal guard semantics, labels, or a bypass flag.
- Step 2 dispatcher implementation-commit retry (separate surface, file later).
- Preflight detect-and-warn for client hook configs (Fix 4 replaces it).

### Approach sketch
- Fix 1: retry the `_commit_run` commit tail (`git add` -> `git diff --cached --quiet` -> `git commit`) exactly once on non-zero rc.
- Fix 2: de-terminalize ship state at Python drive re-entry: reset `ship-pr-state.sh` off `stalled` and neutralize the `finalize-state.sh` terminal overlay before the first `flush_logs_pre`.
- Fix 3: add a dedicated `REFRESH_SKIP_PRETERMINAL_OUTCOME` reason and mirror it at every `REFRESH_SKIP_COMMIT_FAILED` membership/branching site.
- Fix 4: append a `--no-logs-commit` / pre-commit `exclude` remedy to the surfaced detail when the retry still fails on a fixer hook.
- Fix 5: normalize run-log text emission to exactly one trailing newline at a shared write boundary (broad), plus a byte-compare normalization audit in `ship.py`.

### Surfaces in scope
- `python/larch/report/run_log_commit.py` (`_commit_run`), `run_log_flush.py`, `python/larch/core/config.py`.
- `python/larch/implement/ship.py` (re-entry reset + byte-compare), `ship_state.py`, `ship_resume.py`, `step_7a.py`.
- `python/larch/state/_classify.py` (stall-reason routing).
- `python/larch/review/review_tally.py` + shared run-log text write helper (Fix 5 broad).
- Tests under `python/tests/report/` and `python/tests/implement/`.

### Open questions
- None. Operator-approved direction; Fix 5 breadth resolved to broad class-elimination.
