### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1378-1397
- **Concern**: Step 8+ prose still routes on LARCH_STATUS_FILE and monitor_rc after trap removal. Scenario: Stage 3 made larch_quiet_append_done_trap a no-op; collapsing fences removes status-file allocation but L1378 still tells the orchestrator to parse EXIT_CODE from $LARCH_STATUS_FILE and L1397 still distinguishes monitor_rc vs writer_rc — empty/missing status files or wrong stall/bail routing
- **Proposed resolution**: In the implement/SKILL.md edit, explicitly replace post-Invoke guidance (L1378, L1397, and related Step 2/5 wrapper notes) to use the foreground Bash tool exit code plus ship-pr-state.sh keys only; drop monitor_rc / breadcrumb-monitor routing entirely

### FINDING_2:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-quiet.sh:167-171, scripts/test-collect-agent-results.sh:211-221
- **Concern**: Deleted shim functions still have test callers and stale sentinel env coverage. Scenario: After removing larch_quiet_append_done_trap and larch_quiet_write_paired_pid_file from lib-quiet.sh, test-lib-quiet calls undefined functions under set -euo pipefail; the collector test also keeps LARCH_DONE_SENTINEL and LARCH_STATUS_FILE references even though the plan only updates the comment and the final grep gate requires those tokens gone
- **Proposed resolution**: Remove the shim-noop test from test-lib-quiet.sh and strip the obsolete LARCH_DONE_SENTINEL/LARCH_STATUS_FILE setup from the collector C_DONE case, or replace it with an explicit absence-focused assertion if that contract still matters

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/run-step5-review.md:9-11, scripts/collect-agent-results.md:3-4, scripts/dispatch-plan-voters.md:24-25, scripts/ci-wait.md:11-13, scripts/ship-pr.md:183-185
- **Concern**: Script sibling docs retain Family B and paired-PID Stage 3 contracts not named in the plan. Scenario: The PR removes the Family-B fence and shim layer, but shipped sibling docs would still say these scripts are Family B writers or that skill fences carry the historical monitor pair; the script-md sibling rule requires behavior docs to move with script contract changes
- **Proposed resolution**: Add these sibling docs to the UPDATED set and delete or restate only the stale Family B paired-PID sentences without broader rewrites

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-quiet.sh:167-171
- **Concern**: Case 11 still exercises deleted shims. Scenario: Deleting `larch_quiet_append_done_trap` / `larch_quiet_write_paired_pid_file` without updating this harness makes `make test-lib-quiet` fail with `command not found`
- **Proposed resolution**: Add an explicit `### UPDATED: scripts/test-lib-quiet.sh` step to remove or replace case 11 (the plan lists the harness in Testing strategy but not Files to modify)

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-quiet.sh:167-171
- **Concern**: Plan lists make test-lib-quiet in Testing strategy but not in Files to modify; case 11 still invokes removed shims. Scenario: Final grep gate requires zero larch_quiet_append_done_trap / larch_quiet_write_paired_pid_file; test-lib-quiet.sh fails grep and exercises deleted symbols
- **Proposed resolution**: Add scripts/test-lib-quiet.sh to Files to modify: drop or rewrite case 11 after shim removal
