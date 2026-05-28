### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-step0b-router-flag-recovery.sh:55-60
- **Concern**: Finding 1: Case 7 does not actually prove recovery was skipped; the no-file assertion is not independent evidence because recovery_merge_if_needed intentionally leaves a missing run-params.json absent.. Scenario: A future helper/model could call recovery after a failed writer, emit the existing missing-file warning, return non-zero, leave the spy untouched, and still satisfy rc non-zero plus no output file.
- **Proposed resolution**: Capture Case 7 stdout and assert the missing-file recovery warning is absent, or make every recovery invocation go through a spy-marking wrapper before calling recovery_merge_if_needed.

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-step0b-router-flag-recovery.sh:31-40
- **Concern**: Case 7b's planned positive control does not actually prove recovery_merge_if_needed ran. Scenario: The helper writes run-params with --manual-gate-b true, so the 7b jq assertion passes even if write_then_recover touches the spy but omits the recovery call; the plan's stated success-path recovery validation remains unproven
- **Proposed resolution**: Move the spy write to after a checked recovery_merge_if_needed call, for example recovery_merge_if_needed ... || return 1; : > "$spy", and adjust 7b wording to assert recovery completion rather than a merge the writer already performed
