### OOS_1:
- **Description**: Plan states claude-plan-* .launch-stderr is already denied by existing globs, but design_artifact_excluded has no *.launch-stderr arm; the both-externals-down path also writes claude-plan-generic-output.txt.tsv which is outside the cursor/codex-only sidecar list. Scenario: Degraded runs can still flush claude-plan-generic-output.txt.launch-stderr and .tsv to larch-logs/design even after the main fix
- **Reviewer**: Cursor-dyn-fixture-realism
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:13,skills/design/scripts/dispatch-plan-review-panel.sh:99-138,scripts/design-log-publish.sh:303-308
- **Phase**: design

