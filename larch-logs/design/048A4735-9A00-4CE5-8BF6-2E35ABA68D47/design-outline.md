## Proposed Design Outline

### Goals
- Validate generated Mermaid fences in the test harness (not just substring grep).
- Fix skill-filtering in the timing-window awk so non-matching skill round rows cannot contaminate the display.
- Prevent "No review rounds completed." from appearing in live progress during in-flight reviews.
- Sync docs for final-summary and final-report renderers after #4062 Gantt changes.

### Non-goals
- No changes to the Gantt awk path (vendor rows, overlap-only filter stays as-is).
- No changes to the token ledger vendor cost logic.
- No changes to existing Gantt rendering behavior.

### Approach sketch
- Item 1: After test 5b in `test-render-review-phase-detail.sh`, add `python3 cli.py lint mermaid-fences $OUT` assertion.
- Item 2: Update `skills/design/scripts/render-final-summary.md` to document in-progress-vs-no-rounds state and `--no-gantt` suppression contract.
- Item 3: Add `-v SKILL="$SKILL"` and `&& $4==SKILL` to the `rrange` awk in `render-review-phase-detail.sh`; add a contamination test case.
- Item 4: Verify/update `skills/implement/scripts/write-final-report.md` for consistency with revised render-final-summary.md.
- Item 5: Add `_all_round_dirs_inflight()` helper in `progress_report.py`; guard detail-renderer calls in `_render_step5` and `_render_design_plan_review`; add tests.

### Surfaces in scope
- `scripts/test-render-review-phase-detail.sh`
- `scripts/render-review-phase-detail.sh`
- `skills/design/scripts/render-final-summary.md`
- `skills/implement/scripts/write-final-report.md`
- `python/progress_report.py`
- `python/test_progress_report.py`

### Open questions
- None.
