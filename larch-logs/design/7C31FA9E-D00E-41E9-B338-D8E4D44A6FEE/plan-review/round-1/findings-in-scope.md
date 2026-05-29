Validating locations and merging overlapping reviewer findings into the structured aggregator output.
Structured aggregator output from the supplied reviewer findings:

### FINDING_1: Step 8+ still routes on status file and monitor_rc
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: After Stage 3 made `larch_quiet_append_done_trap` a no-op and the PR collapses Family B fences, `skills/implement/SKILL.md` still tells the orchestrator to parse `EXIT_CODE` from `$LARCH_STATUS_FILE` (around L1378) and to distinguish `monitor_rc` vs `writer_rc` (around L1397). Empty or missing status files and wrong stall/bail routing are plausible if post-Invoke guidance is not updated with the trap/fence removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the implement/SKILL.md edit, explicitly replace post-Invoke guidance (L1378, L1397, and related Step 2/5 wrapper notes) to use the foreground Bash tool exit code plus ship-pr-state.sh keys only; drop monitor_rc / breadcrumb-monitor routing entirely

### FINDING_2: Shim removal leaves broken tests and plan gap
- **Reviewer(s)**: unknown-slot, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Removing `larch_quiet_append_done_trap` and `larch_quiet_write_paired_pid_file` from `lib-quiet.sh` without updating harnesses will break `make test-lib-quiet` (case 11 still calls the deleted shims under `set -euo pipefail`). `scripts/test-collect-agent-results.sh` C_DONE still sets `LARCH_DONE_SENTINEL` and `LARCH_STATUS_FILE` while the plan only updates a comment; the final grep gate expects those tokens gone. The plan lists `make test-lib-quiet` in Testing strategy but not `scripts/test-lib-quiet.sh` in Files to modify, so case 11 can fail both tests and the grep gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Remove the shim-noop test from test-lib-quiet.sh and strip the obsolete LARCH_DONE_SENTINEL/LARCH_STATUS_FILE setup from the collector C_DONE case, or replace it with an explicit absence-focused assertion if that contract still matters
  - From Cursor-Innovation: Add an explicit `### UPDATED: scripts/test-lib-quiet.sh` step to remove or replace case 11 (the plan lists the harness in Testing strategy but not Files to modify)
  - From Cursor-Pragmatic: Add scripts/test-lib-quiet.sh to Files to modify: drop or rewrite case 11 after shim removal

### FINDING_3: Script sibling docs still describe Family B / paired-PID
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Concern**: Several script sibling markdown files still describe Family B writers and paired-PID Stage 3 contracts that the plan does not list for update (`run-step5-review.md`, `collect-agent-results.md`, `dispatch-plan-voters.md`, `ci-wait.md`, `ship-pr.md`). After removing the Family B fence and shim layer, shipped docs could contradict runtime behavior; the script-md sibling rule expects behavior docs to move with contract changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add these sibling docs to the UPDATED set and delete or restate only the stale Family B paired-PID sentences without broader rewrites
