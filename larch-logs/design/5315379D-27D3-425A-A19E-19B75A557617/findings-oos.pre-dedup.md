### OOS_1: `step-18.md` still documents the retired two-call no-stall flow
- **Description**: `step-18.md` still documents the retired two-call no-stall flow. Scenario: The plan rewrites `step18-cleanup.md` and SKILL Step 18 branching but does not list `step-18.md`. That file still normatively describes gate-then-finalize as two Bash calls with prompt-side 18a.5 between them, while SKILL keeps `step-18.md` as a Step 18a helper contract (`skills/implement/SKILL.md:901`). Maintainers editing Step 18 can follow stale wrapper docs after the composite fold.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/step-18.md
- **Phase**: design



### OOS_2: Exit matrix still documents standalone orchestrator metadata refresh after ship
- **Description**: Exit matrix still documents standalone orchestrator metadata refresh after ship. Scenario: The plan deletes the Step 8+ `execution-issues refresh` fence and folds refresh into `implement step-8-oos-checkpoint`, but does not update `ship-pr-exit-matrix.md`, which still tells orchestrators to invoke the refresh helper when a tracking issue exists. Future ship-path edits can reintroduce a redundant fence or confuse when refresh runs.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:78-82
- **Phase**: design



### OOS_3: Checkpoint wrapper contract omits folded `refresh_execution_issues(..., best_effort=True)`
- **Description**: Checkpoint wrapper contract omits folded `refresh_execution_issues(..., best_effort=True)`. Scenario: The plan moves refresh into `step8_oos_checkpoint_main()` but does not list updating the step-8-oos-checkpoint sibling contract Python-owned work section. Implementers relying on that doc may omit the in-process call or duplicate refresh at the old ship exit site.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/step-8-oos-checkpoint.md:19-21
- **Phase**: design



