### OOS_1:
- **Description**: Completion-sentinel table still says `.completed/step-1d.5` is batch-written by "Step 2a entry when brainstorm is off" after the plan moves skip-path writes to `--mode entry`. Scenario: Orchestrator/resume readers may still treat Step 2a as the authoritative skip-path writer even though entry now owns it; behavior stays correct only because Step 2a repair is idempotent
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:78-101
- **Phase**: design

