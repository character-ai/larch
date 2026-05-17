# lib-execution-issues.sh

`scripts/lib-execution-issues.sh` is a sourced-only Bash library shared by
`scripts/implement-finalize.sh` and
`skills/implement/scripts/flush-execution-issues.sh`.

Exported functions:

- `sha256_file`
- `sha256_stream`
- `normalize_body_for_hash`
- `json_escape_stream_python`
- `write_execution_issues_records`

Private helper:

- `_lib_warn_line`

The library owns execution-issues markdown splitting, normalized body hashing,
JSON escaping fallback behavior, and NDJSON record composition. See
`skills/implement/scripts/flush-execution-issues.md` for the full pre-bump flush
contract.
