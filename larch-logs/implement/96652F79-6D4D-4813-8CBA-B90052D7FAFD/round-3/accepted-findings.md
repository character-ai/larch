### FINDING_14: Design current-env recovery can preserve stale binary-found values
- **Reviewer(s)**: dyn-presence-gate-output.txt
- **Severity**: latent
- **Concern**: Partial `write-design-current-env.sh` re-invocations can recover prior `*_BINARY_FOUND=true` values when new probe calls omit binary-found flags, letting design degraded-tools classification report a tool as healthy after the CLI disappeared from PATH.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-presence-gate-output.txt: Address the concern above.


### FINDING_2: `step-telemetry-mark.sh` unknown-flag behavior differs from docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The markdown says unknown flags are ignored, but the script exits 0 immediately on the first unknown flag without consuming the remaining argv, silently dropping telemetry work in cases operators may expect to continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: Missing design CLI test for `post_issue` skill forwarding
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CI only asserts `post_issue` forwarding for `--skill implement`; removing `skill=` from the design posting path would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Plan scope expanded beyond approved file list
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch modifies `skills/design/` and other files that the plan reportedly listed as untouched or did not enumerate, making the implement-only workflow-removal scope harder to verify and potentially mixing unrelated fixes into one merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


