## Decision 1: Root cause of circular import
- **Question**: What is the exact cycle and minimal fix point?
- **Resolution**: The cycle is `run_log_flush` → `final_report` → `batch_report` → `run_logs` → `run_log_flush`. `batch_report.py` imports `run_logs` only to call `run_logs.append_execution_issue`, which is defined in `run_log_batch.py` and re-exported by the facade `run_logs.py`. Changing `batch_report.py` to import `append_execution_issue` from `run_log_batch` directly breaks the cycle with a two-line change.
- **Source**: codebase

## Decision 2: Non-goals
- **Question**: Should any other part of the circular chain be changed?
- **Resolution**: No. The `run_logs.py` facade keeps re-exporting `append_execution_issue` unchanged. `final_report.py`, `run_log_flush.py`, and `run_logs.py` are untouched. Only `batch_report.py` changes its import source.
- **Source**: codebase
