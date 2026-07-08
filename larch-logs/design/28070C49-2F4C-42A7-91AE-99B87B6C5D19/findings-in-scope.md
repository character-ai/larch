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
