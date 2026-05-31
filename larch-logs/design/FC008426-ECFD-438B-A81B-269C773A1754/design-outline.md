## Proposed Design Outline

### Goals
- Create `python/ci_monitor.py`: poll CI, classify the outcome (parity with `ci-wait.sh`/`ci-status.sh`/`ci-decide.sh`), drive the CI fixer waterfall on failure, and emit a GOTO-Rebase signal.
- On a real failure: fix ALL failed jobs via the CI vendor waterfall, verify each locally, push once, then signal.
- Full stdlib-only unit coverage with stub `gh` + stub agent waterfall; redacted logs; decision-matrix parity test.

### Non-goals
- No change to `ship-pr.sh` or the live `/implement` path; no `.sh` deletions (cutover is Phase 7).
- No inline rebase — the Phase-7 driver owns the GOTO-Rebase loop; no import of Phase 3/4/5 modules.
- No targeted per-job local fixer (Phase 4 surface); re-drive the CI waterfall capped instead.

### Approach sketch
- New `ci_monitor.py` composes Phase-1 foundation only (`gh`, `agents`, `git`, `redact`, `proc`, `outcomes`, `config`, `retry`).
- Poll loop + status gather (`gh pr checks` bucket + behind-count via the injected `Runner`) + a pure decision matrix porting `ci-decide.sh` ACTIONs and caps.
- On real failure: classify failed jobs (fixable vs no-local-equivalent), collect+redact logs, run `agents.run_waterfall` (`--role fix`), verify each fixable job via its `make` target, stage+commit+push, return GOTO-Rebase.
- Transient first failure → `gh run rerun --failed` only (no fix), transient-retry cap.

### Surfaces in scope
- `python/ci_monitor.py` (new), `python/test_ci_monitor.py` (new).
- `python/config.py` (additive CI caps), `python/README.md` (one layout bullet).
- Read/port: `ci-wait.sh`, `ci-status.sh`, `ci-decide.sh`, `ci-failed-jobs.sh`, `ci-rerun-failed.sh`, `gh-run-logs.sh`, and the `run_evaluate_failure` family in `ship-pr.sh`.

### Open questions
- None. Decoupling (rebase-signal) and per-job fixer scope (re-drive CI waterfall, Phase-1-only) were resolved in Round 1.
