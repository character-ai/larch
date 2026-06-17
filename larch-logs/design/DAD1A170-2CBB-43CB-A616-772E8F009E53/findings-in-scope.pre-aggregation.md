### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_phase_detail.py:53-60
- **Concern**: Implement rounds-root selection only checks run-log dir existence, not whether it contains round-N dirs. Scenario: `progress_report._review_rounds_root` prefers `larch-logs/implement/<run_id>` only when `_round_dirs(run_log_root)` is non-empty; otherwise it falls back to live `IMPLEMENT_TMPDIR`. The plan prefers the run-log dir whenever it exists. Happy-path harnesses create an empty run-log dir (no `round-*/`), so both paths show "No review rounds completed." But when the run-log dir exists (early `mkdir` from run-log init) while completed `round-N/round-meta.json` artifacts still live only under `IMPLEMENT_TMPDIR/round-N/`, the plan would render from an empty root and omit real review detail.
- **Proposed resolution**: Mirror `_review_rounds_root` exactly: use `run_dir` only when `run_dir.is_dir()` and `_round_dirs(run_dir)` is non-empty; otherwise use `implement_tmpdir`. Reuse the same `_round_number` / `_round_dirs` predicates as `progress_report.py`.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_pr_body.py:171-221
- **Concern**: Testing strategy cites make test-write-final-report (pytest -k filter) but issue acceptance requires skills/implement/scripts/test-write-final-report.sh. Scenario: The pytest additions monkeypatch render_implement_review_detail at the call site; the bash harness exercises write_final_report with real render-review-phase-detail.sh and asserts top-reviewer and Gantt output. pytest-only green can hide missing --findings-file or rounds-root wiring until test-harnesses-19 fails.
- **Proposed resolution**: Name the bash harness explicitly in Testing strategy / acceptance (bash skills/implement/scripts/test-write-final-report.sh or make test-harnesses-19). Require at least one test_pr_body.py case that does not monkeypatch the public helper symbol (subprocess layer only), or treat the bash harness as the authoritative /implement integration gate.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/pr_body.py:943-1011
- **Concern**: Plan does not require reordering write_final_report so splice happens before the first body write. Scenario: After render_run_summary the function writes summary-final.md at line 969 and reuses the same pre-splice body for run_dir/final-summary.md, stdout, and upsert; adding detail only to a local variable after that leaves every published sink compact-only
- **Proposed resolution**: Build combined body = append_review_phase_detail(render_run_summary(...), render_implement_review_detail(...)) first; remove or move the line 969 write_text and write the combined body once to summary-final.md, run_dir/final-summary.md, stdout, and upsert

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_pr_body.py
- **Concern**: Implement pytest suite lacks required issue #3794 rounds-root regression. Scenario: Approved outline and skills/implement/scripts/test-write-final-report.sh require that when larch-logs/implement/<RUN_ID>/ exists but round-meta.json lives only under live IMPLEMENT_TMPDIR/round-N/ the final report must not show completed-round table rows. Plan's test_pr_body.py section only lists monkeypatched call-site wiring and marks subprocess-level coverage optional so CI (make test-write-final-report runs pytest only) can pass while reintroducing the path-mismatch bug
- **Proposed resolution**: Add a required test_pr_body.py or test_review_phase_detail.py case mirroring the bash harness #3794 fixture: run-log root present without round-meta live tmpdir has stale round-meta assert upsert body contains ## Review Phase Detail and No review rounds completed and assert completed-round count row is absent

