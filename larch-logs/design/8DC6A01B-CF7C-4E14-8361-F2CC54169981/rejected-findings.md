### [Plan Review] FINDING_1

### FINDING_1: Status port must use quiet_init / emit_kv stdout contract
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned `status_check_main` port must match the machine-readable stdout contract that `skills/status/scripts/status.sh` and other agent CLI mains already use. Today `status.sh` calls `larch_quiet_init` and emits eight contract keys via `emit_kv`; the `/status` skill parses KVs from stdout only. A `status_check_main` that uses plain `print` or stderr diagnostics can interleave non-KV lines, breaking KV parsing and skill rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit requirement: status_check_main must call logging_util.quiet_init and emit the eight contract keys only through logging_util.emit_kv (same pattern as check_reviewers_main / degraded_tools_gate_main)


