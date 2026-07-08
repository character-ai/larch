### OOS_1: [OUT_OF_SCOPE] The proposed shell regression only proves the zero-rc stall happy path. It does not exercise the direct shell wrapper's preserved non-zero commit_rc or malformed/duplicate NEXT_ACTION branches.
- **Description**: [OUT_OF_SCOPE] The proposed shell regression only proves the zero-rc stall happy path. It does not exercise the direct shell wrapper's preserved non-zero commit_rc or malformed/duplicate NEXT_ACTION branches.. Scenario: A regression in skills/implement/scripts/step-5-resume.sh:128-155 could still slip through if the non-zero guard or fail-closed default branch changes, because the new test never hits those cases on the shell path.
- **Reviewer**: Codex-dyn-Shell Dispatch Parity
- **Severity**: minor
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:12-23,44-49
- **Phase**: design



