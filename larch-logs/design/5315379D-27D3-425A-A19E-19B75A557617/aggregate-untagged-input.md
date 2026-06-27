### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-architectural-guidelines-pin-from-staged.sh
- **Concern**: Deleting the Step 16 pin fence without retiring the shipped pin wrapper leaves a G004-dead script. Scenario: The plan folds pinning into `closeout.py` and removes the SKILL launcher, but does not list retiring `step-architectural-guidelines-pin-from-staged.sh`, its `.md` contract, the `scripts/residual-bash-paths.txt` row, or the Extracted Script Registry reference. Runtime reachability today is only the SKILL fence at `skills/implement/SKILL.md:846`; agent-lint G004 scans structured SKILL invocations, so the wrapper becomes unreachable and `make lint` can fail on an otherwise correct fold.
- **Proposed resolution**: Add an explicit retirement step: remove the pin wrapper and contract from the shipped surface (or migrate per `docs/python-migration.md`), drop the registry row, update `residual-bash-paths.txt` / `agent-lint.toml` as needed, and repoint any harness to `architectural_guidelines.pin_note_from_staged` in-process.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/implement/SKILL.md:98
- **Concern**: Extracted Script Registry still indexes wrappers whose SKILL fences are deleted. Scenario: The plan removes the standalone refresh and pin fences but does not require pruning `refresh-execution-issues.md` (`skills/implement/scripts/refresh-execution-issues.sh`) from the Extracted Script Registry. The registry is the orchestrator reachability index; stale rows mis-route future edits and leave `refresh-execution-issues.sh` without a runtime caller once refresh moves in-process into `step8_oos_checkpoint_main()`.
- **Proposed resolution**: In the `### UPDATED: skills/implement/SKILL.md` section, explicitly remove the `refresh-execution-issues` registry row and retire or harness-only the shell wrapper alongside the pin wrapper cleanup.
