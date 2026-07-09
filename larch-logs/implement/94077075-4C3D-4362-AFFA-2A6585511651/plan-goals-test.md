## Goal
Implement issue #6650: [IMPLEMENTING] [BUG] Gantt chart cut off in final report: inflight row cap and all-rows label_width applied to committed final-summary.

## Implementation Plan
## Plan

## Approach

- Keep `PROGRESS_GANTT_ROW_CAP` for live inflight progress output.
- Let committed final reports render every vendor timing row that overlaps each round window.
- Compute `render_gantt` label width from filtered, visible rows only.
- Add a `render_phase_detail` regression that mirrors the existing uncapped-helper cap test: plain `codex-review` rows only, no apply or fallback rows that could mask a dropped tail.
- Extend the shipped `write_final_report` integration test so the same over-cap fixture is asserted in both `summary-final.md` and run-log `final-summary.md`.
- Update the gantt label-width unit test to match visible-row semantics.
- Harden over-cap regression fixtures so a false pass cannot hide late-row truncation behind duplicate labels: require per-index distinct output basenames, assert the unique label for the latest-starting row, and require a minimum visible data-row count of `PROGRESS_GANTT_ROW_CAP + 2`.

## Files to modify/create

### UPDATED: python/larch/report/progress_report.py

- Add a keyword-only `cap` parameter to `_progress_vendor_rows`, defaulting to `PROGRESS_GANTT_ROW_CAP`.
- Apply `_cap_gantt_rows_reserving_apply` only when `cap is not None`.
- Leave existing inflight callers unchanged so live progress keeps the 25-row cap.
- In `_render_phase_gantt`, call `_progress_vendor_rows(..., cap=None)` so final-report charts include all overlapping rows for each attempt window.

### UPDATED: python/larch/rendering/gantt.py

- Change `label_width` to `max(len(row.label) for row, *_ in filtered)` instead of all input `rows`.
- Keep window filtering, explicit `width=`, and the default width formula unchanged except that the formula uses visible-label width.

### UPDATED: python/tests/report/test_progress_report.py

- Add a small shared fixture helper (for example `_write_over_cap_plain_codex_review_rows`) used by both new regression tests:
  - Write `over_cap = PROGRESS_GANTT_ROW_CAP + 2` plain `codex-review` vendor rows.
  - For each index `i` in `range(over_cap)`, call `_write_vendor_timing` with a **distinct** output basename such as `f"codex-specialist-row-{i}-output.txt"` so each row derives a unique label (for example `codex/row-{i}`).
  - Use staggered starts `100 + i` through `100 + over_cap - 1` and a common end time (for example `150`).
  - Do not add coder-apply, gate-b-apply, or fallback rows.
  - Return `over_cap` and the expected latest label (for example `codex/row-{over_cap - 1}`) for assertions.
- Add `test_render_phase_detail_gantt_shows_all_rows_when_over_cap` near the existing `render_phase_detail` Gantt tests.
  - Build one round with the shared over-cap fixture via `_write_round_timing` plus the helper.
  - Call `render_phase_detail(..., timing_ledger=...)`.
  - Assert `### Round 1 reviewer timing` is present.
  - Assert the rendered chart contains the **unique** latest-starting reviewer label for start `100 + over_cap - 1` (for example `codex/row-{over_cap - 1}`), not merely a generic `codex/codex-review` string shared by every row.
  - Assert the chart contains at least `over_cap` visible data rows by counting lines that contain both `│` and `█` (mandatory, not optional).
- Keep existing `_progress_vendor_rows` cap tests as inflight/default behavior coverage; do not weaken `test_progress_vendor_rows_cap_without_apply_keeps_earliest`.

### UPDATED: python/tests/report/test_final_report.py

- Add `test_write_final_report_includes_uncapped_review_timing_gantt` near `test_write_final_report_includes_review_timing_gantt` (lines 97–136).
  - Reuse `_write_minimal_state`, round meta, and `_stub_cost_and_assessment`.
  - Write a round row plus the same distinct-basename over-cap fixture as the `render_phase_detail` regression (import or duplicate the shared helper from `test_progress_report.py` if needed).
  - Call `write_final_report(tmp_path, comment_only=False, skip_tracking_upsert=True)` so both committed outputs are produced.
  - For each of `summary-final.md` and `larch-logs/implement/run1/final-summary.md`:
    - Assert `### Round 1 reviewer timing` is present.
    - Assert a Gantt fence is present (` ``` ` and `█`).
    - Assert the **unique** latest-starting reviewer label for start `100 + over_cap - 1` is present.
    - Assert at least `over_cap` visible data rows by counting lines with both `│` and `█` (same mandatory guard as the unit regression).
  - Assert the chart is not the single-row smoke case from the existing test.

### UPDATED: python/tests/rendering/test_gantt.py

- Replace `test_label_width_uses_all_rows_not_just_filtered` with a test that asserts an out-of-window long label does not set the border column or shrink the visible bar track under default width.
- Keep explicit-`width=` coverage that visible rows still align on the left border.
- Keep edge alignment assertions for visible rows.

## Edge cases

- If every row is outside the window, `render_gantt` still returns `""`.
- If visible labels are long, default-width charts still shrink to stay under the existing width target.
- Final-report attempt splitting stays unchanged; each attempt gets all rows for its own tight window.
- Inflight charts still reserve apply and fallback rows under the cap.
- Over-cap regression fixtures must use only non-reserved reviewer rows so a passing test cannot hide late-row truncation behind reserved slots.
- Over-cap regression fixtures must use per-index distinct output basenames so duplicate labels cannot make a truncated chart look complete.

## Failure modes

- A caller may accidentally pass `cap=None` for live progress and produce a long terminal chart. Avoid changing inflight call sites.
- Reusing one output basename for every over-cap row lets a capped chart pass label assertions while late rows are dropped. Require distinct basenames and minimum data-row counts.
- A row-count assertion may be brittle if chart formatting changes. Pair it with the unique latest-start label assertion; prefer counting lines with both `│` and `█`.
- Long final-report charts may be verbose; that is intended for auditability.
- Testing only `render_phase_detail` or only `comment_only=True` would miss the run-log `final-summary.md` write path.

## Testing strategy

- Run targeted pytest:
  - `cd python && pytest tests/rendering/test_gantt.py tests/report/test_progress_report.py tests/report/test_final_report.py -k 'gantt or label_width'`
- If time permits, run lint for changed Python files:
  - `cd python && ruff check larch/report/progress_report.py larch/rendering/gantt.py tests/report/test_progress_report.py tests/rendering/test_gantt.py tests/report/test_final_report.py`
  - `cd python && pyright larch/report/progress_report.py larch/rendering/gantt.py tests/report/test_progress_report.py tests/rendering/test_gantt.py tests/report/test_final_report.py`

## Acceptance

- Run targeted pytest:
  - `cd python && pytest tests/rendering/test_gantt.py tests/report/test_progress_report.py tests/report/test_final_report.py -k 'gantt or label_width'`
- If time permits, run lint for changed Python files:
  - `cd python && ruff check larch/report/progress_report.py larch/rendering/gantt.py tests/report/test_progress_report.py tests/rendering/test_gantt.py tests/report/test_final_report.py`
  - `cd python && pyright larch/report/progress_report.py larch/rendering/gantt.py tests/report/test_progress_report.py tests/rendering/test_gantt.py tests/report/test_final_report.py`

diff_added: 115
diff_deleted: 18
mechanical_churn: false
diff_lines: 133

## Test plan
(no test plan section in plan-file)
