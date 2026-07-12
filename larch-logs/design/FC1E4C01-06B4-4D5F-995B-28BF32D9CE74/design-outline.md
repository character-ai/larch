## Proposed Design Outline

### Goals
- Consolidate all `larch-logs` corpus-walk logic into `run_log_corpus.py` as the single owner.
- Repoint every bypassing scanner to the shared API; eliminate duplicate `manifest.json`/`run-manifest.json` loops.
- Add a ratchet lint that blocks new out-of-owner walkers from landing.

### Non-goals
- Changing the observable behavior of any existing scanner (pure refactor).
- Modifying the dead-code modules targeted by #7008 (they will be deleted separately).
- Adding new scan features or CLI verbs.

### Approach sketch
- Add four helpers to `run_log_corpus.py`: `run_started_at`, `larch_version`, `round_num_from_path`, `discover_classifications`; all own the `manifest.json`/`run-manifest.json` dual-name fork.
- Repoint nine bypassing callers: `difficulty_calibration`, `_ground_truth`, `rejected_analysis`, `_voting_calibration`, `gc_run_logs`, `final_report`, `audit_runs`, `fluff-analysis.py`, `voter-calibration.py`.
- Add `lint/lint_run_log_walkers.py` (AST grep for `larch-logs` glob/walk patterns outside `run_log_corpus.py`), wire as `lint run-log-walkers`, add Makefile target, add to `lint:` aggregate.

### Surfaces in scope
- `python/larch/report/run_log_corpus.py`
- Seven bypassing Python modules: `difficulty_calibration`, `_ground_truth`, `rejected_analysis`, `_voting_calibration`, `gc_run_logs`, `final_report`, `audit_runs`
- Two skill scripts: `skills/fluff-analysis/scripts/fluff-analysis.py`, `skills/voter-calibration/scripts/voter-calibration.py`
- `python/larch/lint/lint_run_log_walkers.py` (new)
- `python/larch/cli.py`, `Makefile`
- `python/tests/report/test_run_log_corpus.py`

### Open questions
- None.
