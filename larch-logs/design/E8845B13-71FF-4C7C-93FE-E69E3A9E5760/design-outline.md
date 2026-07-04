## Proposed Design Outline

### Goals
- Ensure committed `implement difficulty-rating.json` carries resolved `audit_evaluated`, `audit_upgrade`, `escalations`, and `escalated_round` fields after Step 5 resolution.
- Fix the calibration analyzer so it reports accurate escalation and audit-upgrade rates for implement runs.
- Capture the real rater model in implement difficulty records instead of `"unknown"`.

### Non-goals
- Change design-side difficulty staging (already correct via `design_publish.py`).
- Rewrite the `_refresh_difficulty_record` ship-phase fallback (primary re-staging fix supersedes it for normal runs).
- Change any public CLI or run-log schema fields.

### Approach sketch
- Add `_restage_difficulty_batch(implement_tmpdir, run_id)` helper in `review_and_fix.py` that re-runs `run-log write --batch difficulty-rating` from the resolved tmpdir record; mirrors the `dispatch_step2._write_step2_difficulty_record` flush pattern.
- Call the helper from `_flush_review_batches_for_result` so all terminal exit paths (complete, cap-hit, stall, self-review-required, mav-resume-past-cap) re-stage the resolved record.
- Fix `_render_audit_deltas` filter in `difficulty_calibration.py` from `record.audited` (audit_evaluated=true) to `audit_upgrade=True` only.
- Fix `dispatch_step2._write_step2_difficulty_record` to read the rater model from env/session env instead of hardcoding `"unknown"`.
- Add a regression test verifying complete/cap-hit terminal exits stage a batch with boolean `audit_evaluated`.

### Surfaces in scope
- `python/larch/review/review_and_fix.py`
- `python/larch/calibration/difficulty_calibration.py`
- `python/larch/implement/dispatch_step2.py`
- `python/larch/tests/implement/` or `python/larch/tests/review/` (new regression test)

### Open questions
- None.
