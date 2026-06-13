## Proposed Design Outline

### Goals
- Replace Mermaid `gantt` blocks in reviewer-timing sections with a stdlib-only ASCII Gantt renderer.
- Back the final report (via `render-review-phase-detail.sh`), the progress report (`progress_report.py`), and `/review` from one shared rendering function with no duplicated bar/axis/box logic.

### Non-goals
- Task label corrections (e.g. `cursor/plan-requirements`, `unknown/aggregator`) — deferred.
- Outlier handling (far-right CI `.out` rows compressing real bars) — deferred.
- Changes to timing data collection or `timing-ledger.tsv` format.

### Approach sketch
- Add `python/gantt.py`: pure stdlib function `render_gantt(window_start_s, window_end_s, rows)` with no domain knowledge. Expose as `python3 python/cli.py gantt render` for bash callers.
- In `render-review-phase-detail.sh`: replace the Mermaid emit block with a call to `python3 python/cli.py gantt render`; wrap output in a plain fence.
- In `python/progress_report.py`: import `gantt` directly; after calling `_call_render_phase_detail_script` (still with `--no-gantt`), read `timing-ledger.tsv` and append per-completed-round ASCII Gantt blocks.
- Add `python/gantt.md` (sibling contract) and `python/test_gantt.py` (tests).
- Update `scripts/test-render-review-phase-detail.sh` with 4 spec assertions; update `render-review-phase-detail.md` "Mermaid timing format" prose.

### Surfaces in scope
- `python/gantt.py` (new) + `python/gantt.md` (new) + `python/test_gantt.py` (new)
- `python/cli.py` (add `gantt render` entry)
- `scripts/render-review-phase-detail.sh` + `.md`
- `python/progress_report.py` + `python/test_progress_report.py`
- `scripts/test-render-review-phase-detail.sh` + `.md`

### Open questions
- None.
