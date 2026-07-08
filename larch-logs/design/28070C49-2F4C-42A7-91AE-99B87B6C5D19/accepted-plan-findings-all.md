### FINDING_1: Nested `aggregated_output` still triggers false-positive kills
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `_codex_policy_rejection_excerpt` still appears to match trigger phrases inside nested `item.aggregated_output` from completed Codex JSONL events, so healthy agents can be fast-killed unless the parser strips nested output before regex scanning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Recursively walk each parsed JSON line and delete aggregated_output inside nested dicts (at minimum item). Re-serialize the line before regex scanning.
  - From Cursor-Innovation: Add recursive aggregated_output removal across all dict nodes in the JSON tree (or explicitly pop item.aggregated_output) before regex scanning; confirm against larch-logs/design/693522DE execution-issues.md event shape
  - From Cursor-Pragmatic: Specify that `_strip_aggregated_output_from_json_lines` removes `aggregated_output` from nested `item` dicts (or recursively from any dict in the parsed tree), then re-serialize the line before regex scanning.
  - From Cursor-Requirements: Specify recursive removal of aggregated_output from every dict in each parsed JSON line at least item.aggregated_output. Shape test_run_external_agent_codex_policy_no_false_positive_aggregated_output as item.completed with nested item.aggregated_output holding both trigger phrases.


### FINDING_2: Strip only successful completions
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Removing `aggregated_output` from every JSON line would also hide genuine policy-rejection evidence in failed command rows; the cleanup needs to be gated so only successful completions are stripped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When removing aggregated_output, gate on the owning command object: strip only when exit_code is 0 (or null on in-progress rows with empty output); preserve aggregated_output when exit_code is non-zero. Add the false-positive regression fixture as nested item.completed with exit_code==0 and trigger phrases inside item.aggregated_output.


### FINDING_3: Regression fixture must match nested Codex envelope
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The new false-positive regression can pass with a flat `aggregated_output` fixture even though production Codex JSONL nests the field under `item` in `item.completed` events, so the test may not catch the real false-positive path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Write the fixture as {"type":"item.completed","item":{...,"aggregated_output":"exec_command failed ... Rejected(blocked by policy) ...","exit_code":0,"status":"completed"}} and assert no kill plus no FAILURE_CLASS=policy-rejection in diag
  - From Cursor-Pragmatic: Write `test_run_external_agent_codex_policy_no_false_positive_aggregated_output` with a realistic `item.completed` / `command_execution` JSONL line (`exit_code` 0, `status` completed) whose nested `item.aggregated_output` quotes `exec_command failed` and `Rejected(blocked by policy)`, and assert the process is not killed and diag lacks `FAILURE_CLASS=policy-rejection`.


### FINDING_1: Integration test fixture cannot survive launch-time truncation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The planned false-positive regression test relies on pre-writing `paths.events` before `run_external_agent` starts, but launcher prep removes or truncates that file on child startup. As written, the stub can leave an empty events stream, so the test would pass vacuously without exercising the nested `exit_code: 0` / `aggregated_output` sanitization path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Have the stub child print the nested `item.completed` JSONL line to stdout (events sink) on startup, then sleep; do not rely on pre-launch writes.
  - From Cursor-Innovation: Have the long-sleep stub print the nested `item.completed` JSONL line (with exit_code 0 and trigger phrases in item.aggregated_output) to stdout, mirroring test_run_external_agent_codex_policy_rejection_fast_fails; keep poll_interval low and assert no early policy-rejection kill
  - From Cursor-Pragmatic: Have the stub child print/flush the nested `item.completed` JSONL line to stdout (then sleep), matching test_run_external_agent_codex_policy_rejection_fast_fails. Optionally drop the pre-write step entirely.
  - From Cursor-Requirements: Have the stub child emit the nested `item.completed` JSONL line (exit_code 0, trigger phrases inside item.aggregated_output) to stdout with flush before sleeping, or append that line after launch starts; do not rely on pre-writing paths.events


### FINDING_2: Strip-gating contract for aggregated_output is underspecified and can over-strip
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The recursive sanitizer’s contract is inconsistent: the plan says to preserve `aggregated_output` when `exit_code` is absent/null and output is non-empty, but the walker only passes `exit_code` into `_should_strip_aggregated_output`. That can cause all `exit_code is None` rows to be stripped, including in-progress nodes that already contain meaningful output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make one contract: pass both `exit_code` and `aggregated_output` into `_should_strip_aggregated_output`, strip only on `exit_code == 0` or falsy empty output, and recurse with that rule.
  - From Cursor-Innovation: In _strip_gated_aggregated_output, pop aggregated_output only when exit_code == 0, or when exit_code is None and aggregated_output is falsy; when exit_code key is absent, preserve per failure mode 1


