# lib-redact.sh contract

`scripts/lib-redact.sh` contains source-able pre-redaction trimmers used before
payloads enter the normal `larch-log.sh` tmpdir and secrets redaction pipeline.

Functions:

- `larch_redact_strip_meta_cmd_json INPUT OUTPUT` copies a line-oriented `.meta`
  sidecar while dropping any physical line that starts with `CMD_JSON=`.
- `larch_redact_strip_cursor_json_result INPUT OUTPUT` copies a Cursor JSON
  sidecar while removing the top-level `.result` field. It uses `jq` when
  available, falls back to Python's standard JSON parser, and finally copies the
  input unchanged if neither structured parser can process the file.

Callers own temp-file creation and atomic publication. These helpers do not
perform tmpdir path or secret redaction; callers should pass their output through
`larch_log_redact_file` before writing durable artifacts.
