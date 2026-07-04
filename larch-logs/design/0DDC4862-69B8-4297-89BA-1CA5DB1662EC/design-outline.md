## Proposed Design Outline

### Goals
- Make the `voting write-tally` failure visible: capture subprocess stderr/stdout to `code-review-tally.flush.err` in both call sites, and surface the nonzero rc as an execution-issues Warnings entry (serves G-Py-4).
- Stop summaries and PR bodies rendering `Code review: N/A`: derive the line from `review-findings-full.jsonl` when `code-review-tally.json` is absent.
- Leave a committed trace so the next live run reveals the mechanism.

### Non-goals
- Fixing the actual write-tally failure mechanism. It is unknown and deferred until a live `.flush.err` capture reveals it.
- Back-filling `code-review-tally.json` for the v52.2.4..v52.4.2 window (separate follow-up PR).
- Removing a `CODE_REVIEW_LINE` ship-handoff branch. None exists in `final_report.py` today.

### Approach sketch
- `batch_report.py::flush_review_batches`: mirror the findings leg. Write `code-review-tally.flush.err` on nonzero rc, unlink on success. Add an execution-issues Warnings entry.
- `review_and_fix.py::write_self_review_tally`: add the same `.flush.err` capture. Keep its existing Warnings entry.
- `final_report.py`: when `code-review-tally.json` is missing, fall back to counting `review-findings-full.jsonl` code-review records, reusing the existing `_derive_code_review_tally` counting shape.

### Surfaces in scope
- `python/larch/review/batch_report.py`
- `python/larch/review/review_and_fix.py`
- `python/larch/report/final_report.py`
- Their tests under `python/tests/`.

### Open questions
- None.
