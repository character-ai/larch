### [Plan Review] FINDING_1

### FINDING_1: Pin wrapper retirement missing from plan
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Concern**: Deleting the Step 16 pin fence without retiring the shipped pin wrapper leaves a G004-dead script. Scenario: The plan folds pinning into `closeout.py` and removes the SKILL launcher, but does not list retiring `step-architectural-guidelines-pin-from-staged.sh`, its `.md` contract, the `scripts/residual-bash-paths.txt` row, or the Extracted Script Registry reference. Runtime reachability today is only the SKILL fence at `skills/implement/SKILL.md:846`; agent-lint G004 scans structured SKILL invocations, so the wrapper becomes unreachable and `make lint` can fail on an otherwise correct fold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit retirement step: remove the pin wrapper and contract from the shipped surface (or migrate per `docs/python-migration.md`), drop the registry row, update `residual-bash-paths.txt` / `agent-lint.toml` as needed, and repoint any harness to `architectural_guidelines.pin_note_from_staged` in-process.


### [Plan Review] FINDING_2

### FINDING_2: Extracted Script Registry not pruned for refresh wrapper
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Extracted Script Registry still indexes wrappers whose SKILL fences are deleted. Scenario: The plan removes the standalone refresh and pin fences but does not require pruning `refresh-execution-issues.md` (`skills/implement/scripts/refresh-execution-issues.sh`) from the Extracted Script Registry. The registry is the orchestrator reachability index; stale rows mis-route future edits and leave `refresh-execution-issues.sh` without a runtime caller once refresh moves in-process into `step8_oos_checkpoint_main()`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the `### UPDATED: skills/implement/SKILL.md` section, explicitly remove the `refresh-execution-issues` registry row and retire or harness-only the shell wrapper alongside the pin wrapper cleanup.
```


### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/implement_dispatch.py
- **Concern**: [SCOPE-REDUCTION] Reimplementing `run_gate` in Python duplicates `step-18.sh` stall-layer logic. Scenario: The plan adds `_stall_layer_active`, `_resolve_stall_memory_layer`, and file readers in `implement_dispatch.py` to mirror `step-18.sh:108-167`. That is the largest new complexity block and the accepted parity-risk surface (memory `case` binding, OR-of-four-layers). Any drift spuriously routes `NEXT_ACTION=stall-recovery` or runs green-path finalize while a stall layer is active.
- **Proposed resolution**: Inside `step_18_gate_finalize_main()`, subprocess `bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate --stall-tracking-memory …`, parse `STALL_RECOVERY_REQUIRED` and `STALL_TRACKING_*` from that capture, then branch. Keep only `normalize-outcome`, escalation-evidence checks, and finalize chaining in Python; document any new subprocess sites for the ratchet.


