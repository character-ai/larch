## Proposed Design Outline

### Goals
- Break the circular import `run_log_flush → final_report → batch_report → run_logs → run_log_flush`.
- Allow `test_run_log_flush.py` to collect and run without ImportError.

### Non-goals
- Changing the `run_logs.py` facade re-export surface.
- Modifying `final_report.py`, `run_log_flush.py`, or `run_logs.py`.
- Adding lazy-import wrappers or function-scoped imports.

### Approach sketch
- In `batch_report.py`, replace `from larch.report import run_logs` with `from larch.report import run_log_batch`.
- Update the two `run_logs.append_execution_issue(...)` call sites to `run_log_batch.append_execution_issue(...)`.
- `run_log_batch.py` only imports `larch.core` and `larch.errors`; no cycle can re-form.

### Surfaces in scope
- `python/larch/review/batch_report.py` (one import line + two call sites)

### Open questions
- None.
