## Proposed Design Outline

### Goals
- Flush code-review batches (`code-review-tally.json`, `review-findings-full.jsonl`) on the `cap-hit` and `complete` Step 5 loop terminal paths, mirroring the existing `stall` / `self-review-required` flush calls.
- Replace the blanket `contextlib.suppress(Exception)` in `_flush_review_batches_for_result` with surfaced failures (stderr + execution-issues `Warnings` entry), matching the `write_self_review_tally` precedent.
- Drop the dead `CODE_REVIEW_LINE` `_read_kv` branch in `final_report.py` so the tally-file derivation is the single source for the `Code review` line.
- Add regression tests proving `complete` and `cap-hit` loop exits leave populated run-root tally/findings files.

### Non-goals
- Do not touch the `mav-resume-past-cap` stub flush (`rounds_completed=0, result=None`) at review_and_fix.py:600.
- Do not backfill already-committed 2026-07-03 run-log directories with regenerated run-root files.
- Do not change `--self-review` tally emission (`write_self_review_tally`); it is unaffected by this bug.

### Approach sketch
- Add `_flush_review_batches_for_result(...)` calls at the `cap-hit` and `complete` terminal branches in `step5()`, before `_emit_step5_envelope`, mirroring the existing stall-path ordering.
- Replace the `contextlib.suppress(Exception)` wrapper with a try/except that logs via `_err` and appends an execution-issues `Warnings` entry.
- Remove the `CODE_REVIEW_LINE` `_read_kv` fallback in `_derive_final_report_fields`, deriving `code_line` directly from the tally file.
- Extend test coverage for both terminal paths and the removed fallback branch.

### Surfaces in scope
- `python/larch/review/review_and_fix.py` (`step5`, `_flush_review_batches_for_result`)
- `python/larch/report/final_report.py` (`_derive_final_report_fields`)
- `python/tests/review/test_review_and_fix.py`
- `python/tests/report/test_final_report.py`

### Open questions
- None.
