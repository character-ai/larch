## Proposed Design Outline

### Goals
- Include phase2/phase3 fallback timing rows in the round reviewer Gantt chart.
- Label fallback rows with a distinct "(via fallback)" suffix so operators can distinguish the primary attempt from the fallback run.

### Non-goals
- No changes to Top-reviewers scoring or `_apply_fallback_remap` logic.
- No changes to the timing ledger format or `record_vendor_task`.
- No changes to how `_progress_normalize_output_base` is used in other contexts.

### Approach sketch
- Fix `_derive_progress_label` in `python/larch/report/progress_report.py` to normalize the output basename (strip `-phase2`/`-phase3`) before the label_map lookup and before calling `_progress_derived_label`.
- When the normalized basename differs from the raw basename (i.e., it is a fallback row), append " (via fallback)" to the derived label.
- Add a regression test in `python/tests/report/test_progress_report.py` covering the phase2 row label and the end-to-end `_progress_vendor_rows` call.

### Surfaces in scope
- `python/larch/report/progress_report.py` (`_derive_progress_label`)
- `python/tests/report/test_progress_report.py`

### Open questions
- None.
