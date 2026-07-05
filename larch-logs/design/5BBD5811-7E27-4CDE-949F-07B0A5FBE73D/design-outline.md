## Proposed Design Outline

### Goals
- Record the compose-time guideline outcome (shipped/clean/dropped + reason) in the committed implement run log on every run that reaches Step 8.
- Add an audit scan handler so committed logs can report the implement guideline drop rate.

### Non-goals
- Change guideline note composition, assessment, or re-author logic.
- Modify pre-Step-8 flush timing or the execution-issues flush pipeline.
- Retroactively backfill historical run logs.

### Approach sketch
- After `_guidelines_gate_before_pr` returns in `ship.py`, write a small JSON record to tmpdir: outcome (`shipped`/`clean`/`dropped`), `note_kind`, and `drop_reason` when applicable.
- Register a new `guideline-ship-outcome` batch in `run_log_batch.py` (append mode, json-lines sanitizer) and include it in `_stage_pre_commit` to land it in the committed log directory.
- Add `_guideline_ship_outcome_scan_obj` to `audit_runs.py`, register in `_NAMED_RUN_SCAN_HANDLERS`, and add a row to `scans-implement.tsv`.
- Add unit tests for the outcome writer and the scan handler.

### Surfaces in scope
- `python/larch/implement/ship.py` (call outcome writer after guidelines gate)
- `python/larch/implement/ship_guidelines.py` (outcome write helper, possibly)
- `python/larch/report/run_log_batch.py` (new batch slug)
- `python/larch/report/run_log_flush.py` (`_stage_pre_commit` inclusion)
- `python/larch/issue/audit_runs.py` (scan handler + `_NAMED_RUN_SCAN_HANDLERS`)
- `.claude/skills/audit-runs/scans-implement.tsv`
- `python/tests/implement/test_ship.py` and `python/tests/issue/test_audit_runs.py`

### Open questions
- Should `guideline-ship-outcome.json` be added to `docs/run-logs-required-files.tsv` under a `step8` condition?
