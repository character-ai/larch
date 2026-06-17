### FINDING_6: Truncation-marker detection must run after `redact_outbound`, not on raw renderer stdout
- **Reviewer(s)**: Cursor-dyn-redaction-path
- **Severity**: important
- **Concern**: Checking raw renderer stdout for `[content truncated` before `redact_outbound` is unsafe: PEM handling in `python/redact.py` can introduce that marker during redaction, so pre-redact detection can miss leaked truncated content that then reaches chat and upsert paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-redaction-path: Reorder the contract: run `text = redact.redact_outbound(renderer_stdout)` only after subprocess success/non-empty checks; then `if "[content truncated" in text: return ""`; otherwise return `text`. Keep truncation detection post-redact, matching `tracking_issue.py` and the Edge cases bullet at plan line 151.


### FINDING_8: Tests must exercise the helper's subprocess failure swallow path, not only call-site monkeypatch
- **Reviewer(s)**: Cursor-dyn-best-effort-contract
- **Severity**: important
- **Concern**: Monkeypatching `render_*_review_detail` to return `""` proves call-site wiring only. A helper that raises on non-zero exit, timeout, or missing `jq` would still fail `/design` final summary or `/implement` `write_final_report` with no test signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-best-effort-contract: Add `python/test_review_phase_detail.py` (or extend the planned tests) with at least: (a) `subprocess.run` returning non-zero, (b) `subprocess.TimeoutExpired`, and (c) empty stdout; assert helper returns `""`. For design, add one `render_final_summary_main` test (monkeypatch subprocess or the helper) asserting exit code stays `0` when the renderer fails.




### FINDING_2: Test plan can let rounds-root and splice wiring regress in CI
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan's testing strategy leans on pytest additions that monkeypatch `render_implement_review_detail` at the call site, while issue acceptance and the existing bash harness (`skills/implement/scripts/test-write-final-report.sh`, including the #3794 path-mismatch fixture) exercise real `write_final_report` → `render-review-phase-detail.sh` wiring. `make test-write-final-report` runs pytest only, so pytest-only green can hide missing `--findings-file` or rounds-root wiring until `make test-harnesses-19` fails. The plan also lacks a required pytest regression mirroring #3794: run-log root present but `round-meta.json` only under live `IMPLEMENT_TMPDIR/round-N/` must not render completed-round table rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Name the bash harness explicitly in Testing strategy / acceptance (bash `skills/implement/scripts/test-write-final-report.sh` or `make test-harnesses-19`). Require at least one `test_pr_body.py` case that does not monkeypatch the public helper symbol (subprocess layer only), or treat the bash harness as the authoritative /implement integration gate.
  - From Cursor-Requirements: Add a required `test_pr_body.py` or `test_review_phase_detail.py` case mirroring the bash harness #3794 fixture: run-log root present without round-meta, live tmpdir has stale round-meta; assert upsert body contains `## Review Phase Detail` and `No review rounds completed.` and assert completed-round count row is absent.



