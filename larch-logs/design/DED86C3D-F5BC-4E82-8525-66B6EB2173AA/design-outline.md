## Proposed Design Outline

### Goals
- Remove duplicate Python timing-row extraction from `progress_report.py` (Item 1): shell script becomes the single owner
- Fix `docs/linting.md` and `.github/workflows/ci.yaml` to remove stale Mermaid-for-harness references (Item 2)
- Fix `scripts/render-review-phase-detail.md` to document the `--skill` filter split between Time and Gantt windows (Item 3)
- Fix `docs/python-migration.md` to reflect the scoped `.claude/skills/**/*.md` bare-basename check (Item 4)

### Non-goals
- Item 5 (`[OUT_OF_SCOPE]`): no fix for `docs/linting.md:174` / `AGENTS.md` lint-retired-scripts claim
- No new tests for shell-side Gantt generation (already covered by `test-render-review-phase-detail.sh`)
- No architectural changes to `render-review-phase-detail.sh` itself

### Approach sketch
- `progress_report.py`: delete `_timing_lines`, `_progress_round_windows`, `_progress_vendor_rows`, `_render_progress_timing_charts` and associated constants + gantt import; remove `--no-gantt` from shell call; simplify `_render_review_detail` and `_render_design_review_detail` to single-call delegates
- `test_progress_report.py`: remove 7 tests and 2 helper functions that test the now-deleted Python Gantt code
- `.github/workflows/ci.yaml`: remove shard-12 Mermaid setup-node / npm-cache / npm-ci steps
- `docs/linting.md`: remove two sentences that say `test-harnesses-12` installs Mermaid CLI for the renderer harness
- `scripts/render-review-phase-detail.md`: update Time bullet to say round windows are filtered by `--skill`; clarify that Gantt windows are not filtered
- `docs/python-migration.md`: update "never matches repo-wide bare basenames" to describe the scoped `.claude/skills/**/*.md` basename check

### Surfaces in scope
- `python/progress_report.py`
- `python/test_progress_report.py`
- `.github/workflows/ci.yaml`
- `docs/linting.md`
- `scripts/render-review-phase-detail.md`
- `docs/python-migration.md`

### Open questions
- None.
