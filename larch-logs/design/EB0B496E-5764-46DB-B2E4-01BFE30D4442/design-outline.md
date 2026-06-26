## Proposed Design Outline

### Goals
- Prevent long reviewer labels from causing visual corruption in the Gantt chart
- Keep total Gantt chart line width within a reasonable display bound (~90 chars)
- Fix is confined to `gantt.py` and its tests

### Non-goals
- Changing label generation logic in `progress_report.py`
- Truncating or abbreviating displayed labels
- Changing the DEFAULT_WIDTH constant
- Fixing any display-specific rendering issues outside Python code

### Approach sketch
- In `render_gantt`, after computing `label_width` and `duration_width`, compute `effective_width = min(width, max(10, 90 - label_width - duration_width - 4))`
- Replace `width` with `effective_width` for all subsequent bar, axis, and box computations
- This keeps total line width ≤ 90 for labels of any length, while not changing behavior for short labels (≤ 26 chars with default width=56)
- Add one test in `test_gantt.py` verifying that a 34-char label chart stays within the bound

### Surfaces in scope
- `python/gantt.py` — width-capping logic in `render_gantt`
- `python/test_gantt.py` — new test for long-label width capping

### Open questions
- None.
