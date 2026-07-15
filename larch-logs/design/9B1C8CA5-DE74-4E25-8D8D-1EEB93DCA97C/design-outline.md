## Proposed Design Outline

### Goals
- Remove 162 re-export imports from `run_logs.py`, leaving only 26 locally-defined items.
- Remove 20 private re-export-only imports from `analyze_issues.py`.
- Repoint all affected callers and tests to the defining sub-modules; regenerate baseline JSON files.

### Non-goals
- Do not change other #7010 pieces: `review_pipeline.py`, `design_lifecycle.py`, cli.py table merge.
- Do not change logic in `run_logs.py`'s locally-defined functions.
- Do not migrate callers beyond those named in the issue scope.

### Approach sketch
- Strip re-export import blocks (lines 41-200) from `run_logs.py`; keep only locally-defined items and imports they require.
- Repoint 6 named production callers to their designated sub-modules (`run_log_batch`, `run_log_manifest`, `run_log_commit`, `run_log_flush`).
- Identify and remove 20 private re-export-only imports from `analyze_issues.py`.
- Repoint `voter-calibration.py`, `test_analyze_issues.py`, and `test_run_logs.py` to sub-modules.
- Regenerate 3 baseline JSON files; update `python/README.md`.

### Surfaces in scope
- `python/larch/report/run_logs.py`
- `python/larch/issue/analyze_issues.py`
- `python/larch/implement/step_7a.py`, `python/larch/issue/oos_filer.py`
- `python/larch/design/design_publish.py`, `python/larch/design/design_log_publish_flow.py`
- `python/larch/review/review_and_fix.py`, `python/larch/issue/file_oos.py`, `python/larch/state/finalize.py`
- `skills/voter-calibration/scripts/voter-calibration.py`
- `python/tests/issue/test_analyze_issues.py`, `python/tests/report/test_run_logs.py`
- `python/monkeypatch-facade-binding-baseline.json`, `python/keyword-only-baseline.json`, `python/suppression-reason-baseline.json`
- `python/README.md`

### Open questions
- None.
