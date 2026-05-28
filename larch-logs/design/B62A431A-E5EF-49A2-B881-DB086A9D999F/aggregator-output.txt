### FINDING_1: Case 7 does not independently prove recovery was skipped
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Case 7 can pass even if recovery is attempted after a failed writer, because a missing `run-params.json` remains absent and the existing assertions only check non-zero exit plus no output file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Capture Case 7 stdout and assert the missing-file recovery warning is absent, or make every recovery invocation go through a spy-marking wrapper before calling recovery_merge_if_needed.

### FINDING_2: Case 7b positive control does not prove recovery completed
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Case 7b can pass even if `write_then_recover` touches the spy but never calls `recovery_merge_if_needed`, because the helper writes `run-params` with `--manual-gate-b true` before the recovery path being tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Move the spy write to after a checked recovery_merge_if_needed call, for example recovery_merge_if_needed ... || return 1; : > "$spy", and adjust 7b wording to assert recovery completion rather than a merge the writer already performed
