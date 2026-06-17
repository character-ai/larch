## Proposed Design Outline

### Goals
- Restore the per-round review table + ASCII Gantt in the `/design` final summary (`design_summary.py`) and the `/implement` final report (`pr_body.py`).
- Show the detail in chat AND the upserted public comment, redacting the spliced content before the public upsert.
- Turn the currently-RED `test-write-final-report.sh` green; add `/design` coverage.

### Non-goals
- No new timing-ledger / round-meta writes. Reuse existing data; Gantt degrades gracefully when timing rows are absent.
- No change to `render-review-phase-detail.sh` rendering logic or the live `p` report (`progress_report.py`).
- No change to the compact `render run-summary` block format.

### Approach sketch
- Reuse the live-report path: invoke `render-review-phase-detail.sh --skill design|implement` over the rounds-root, mirroring `progress_report.py::_render_design_review_detail` / `_render_review_detail`.
- `design_summary.py`: after `invoke_render` writes `final-summary.md`, splice the redacted detail in before the stdout emit and the `tracking-issue upsert-summary`.
- `pr_body.py::write_final_report`: after `render_run_summary`, splice the redacted detail into the body before `summary-final.md` write and upsert.
- Factor one best-effort splice helper (swallows renderer failures) so both stay in sync.

### Surfaces in scope
- `python/design_summary.py`, `python/pr_body.py` (splice sites).
- `python/test_design_summary.py` (new), `skills/implement/scripts/test-write-final-report.sh` (already asserts it; goes green).
- `scripts/render-review-phase-detail.md` (reconcile contract).
- A small shared splice helper (reuse `progress_report.py` helpers or a new module).

### Open questions
- Compose `review-findings-full.jsonl` for `/design` to populate the "Top reviewers" sub-section, or render table + Gantt only? Lean: point at it where present, degrade gracefully when absent (design currently omits it).
