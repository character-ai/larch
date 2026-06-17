## Acceptance

- `/design` final summary (`design_summary.py::render_final_summary_main`, post phase) includes the `## Review Phase Detail` table and, when timing rows exist, the `### Round N reviewer timing` ASCII Gantt. The detail shows in chat AND the upserted public issue comment, redacted via `redact_outbound`.
- `/implement` final report (`pr_body.py::write_final_report`) includes the same `## Review Phase Detail` section. `make test-write-final-report` is green, including the #3794 rounds-root regression (run-log root selected when it exists, even with no completed rounds).
- `python/review_phase_detail.py` returns `""` and never raises on missing script/root, subprocess error, `TimeoutExpired`, non-zero renderer exit, empty stdout, or a post-`redact_outbound` `[content truncated` marker. A renderer failure leaves both final reports emitting the compact run-summary block and exit 0.
- `scripts/render-review-phase-detail.sh` and the live `p` report (`python/progress_report.py`) are unchanged.
- `scripts/render-review-phase-detail.md` names the restored Python callers and drops the stale `write-final-report.sh` invokes-renderer claim.
- New/updated pytest is green: `python/test_review_phase_detail.py`, `python/test_design_summary.py`, `python/test_pr_body.py` (including subprocess-layer #3794 coverage).
- `make lint`, `make py-lint`, and `make py-test` pass.
