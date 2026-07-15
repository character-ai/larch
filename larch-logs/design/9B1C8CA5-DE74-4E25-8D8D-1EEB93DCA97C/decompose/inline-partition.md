## Pieces

### Piece 1: run_logs.py facade shrink and caller repointing
- Scope: Remove 162 re-export imports from python/larch/report/run_logs.py, keeping 26 locally-defined items; repoint design_publish.py, design_log_publish_flow.py, review_and_fix.py, file_oos.py to run_log_batch; repoint finalize.py to run_log_manifest and run_log_commit; repoint oos_filer.py to run_log_manifest; repoint step_7a.py to run_log_flush; update test_run_logs.py; regenerate all three baselines.
- Firm-headings: python/larch/report/run_logs.py, python/larch/design/design_publish.py, python/larch/design/design_log_publish_flow.py, python/larch/review/review_and_fix.py, python/larch/issue/file_oos.py, python/larch/state/finalize.py, python/larch/issue/oos_filer.py, python/larch/implement/step_7a.py, python/tests/report/test_run_logs.py, python/monkeypatch-facade-binding-baseline.json, python/keyword-only-baseline.json, python/suppression-reason-baseline.json
- Acceptance: python -c "import larch.report.run_logs; assert not hasattr(larch.report.run_logs,'effective_run_id')" passes; make py-lint passes; monkeypatch-facade lint passes
- Dependencies: none
- Size estimate: ~500 lines

### Piece 2: analyze_issues.py facade shrink, caller repointing, and README
- Scope: Remove 20 private re-export-only imports from python/larch/issue/analyze_issues.py; repoint voter-calibration.py and test_analyze_issues.py to sub-modules; re-regenerate all three baselines to capture remaining analyze_issues changes; update python/README.md.
- Firm-headings: python/larch/issue/analyze_issues.py, skills/voter-calibration/scripts/voter-calibration.py, python/tests/issue/test_analyze_issues.py, python/monkeypatch-facade-binding-baseline.json, python/keyword-only-baseline.json, python/suppression-reason-baseline.json, python/README.md
- Acceptance: python -c "import larch.issue.analyze_issues; assert not hasattr(larch.issue.analyze_issues,'_join_implement_run_records')" passes; make py-lint passes; monkeypatch-facade lint passes
- Dependencies: blocked-by Piece 1
- Size estimate: ~150 lines
