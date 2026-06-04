### [Plan Review] FINDING_7

### FINDING_7: Step 5d footer must be qualified after early rename
- **Reviewer(s)**: Cursor-dyn-admission-flow
- **Severity**: important
- **Concern**: The Step 5d failed-publish footer remains unconditional after early `[DESIGNED]` rename. With `PUBLISH_OK=false` and title admission already ready, the footer can still read as requiring continuation rather than separating `/implement` readiness from log recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-admission-flow: Apply the plan's RENAMED/title qualification to the Step 5d footer itself (not only render-final-summary.md): when RENAMED=true or title is [DESIGNED], state that /implement may proceed and log recovery is separate; when RENAMED=false, point to the [DESIGNED] rename failed WARN### OOS_1:
- **Description**: No unit tests for --scrub-only mode. Scenario: Worktree/scrub contract regressions undetected until live /design
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-log-publish.sh
- **Phase**: design


