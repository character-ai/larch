# Run-log batch registry

Run-log batches are registered in `python/larch/report/run_logs.py`.

Each batch declares:

- **extension**: the on-disk suffix.
- **mode**: `replace` or `append`.
- **sanitizer**: `none`, `json-object`, `json-lines`, or a specialized
  sanitizer.

The Python CLI validates the batch name before writing.
Append-mode batches must use `run-log append`.
Replace-mode batches must use `run-log write`.

The registry includes the durable implement, review, design, token, timing,
execution-issue, transcript, and vendor-diagnostic carriers.
