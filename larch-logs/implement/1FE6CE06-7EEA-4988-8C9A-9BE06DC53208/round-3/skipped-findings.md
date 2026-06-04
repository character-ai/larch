### FINDING_15: failed-publish renderer changes and DESIGN_LOG_* interface are unplanned
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The diff modifies renderer-related files and adds a `failed-publish` outcome plus `DESIGN_LOG_*` env interface, but the plan did not list those files or requirements; related tests may therefore be either necessary but unplanned or over-constraining depending on whether the new outcome is formalized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add `skills/design/SKILL.md`, `skills/design/scripts/render-final-summary.sh`, `skills/design/scripts/render-final-summary.md`, and `skills/design/scripts/test-render-final-summary.sh` to the plan's "Files to modify/create" section with the `failed-publish` outcome requirements, and document the new `DESIGN_LOG_*` env-var interface between `design-publish.sh` and `render-final-summary.sh`.
  - From cursor-specialist-plan-fidelity-output.txt: If `failed-publish` is formally added to the plan, the assertion is correct; if not, relax the assertion to check only that `post-publish-only` is called.



### FINDING_6: Unplanned plan-review-loop and multi-round integration changes reduce traceability and leave stderr buffering behavior under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `plan-review-loop.sh` and `test-design-multi-round-integration.sh` changed outside the plan’s affected-files list. The stderr-forwarding change also changes streaming behavior to buffered replay without a dedicated regression assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: add `skills/design/scripts/plan-review-loop.sh` (and its sibling `.md`) to the plan's files list with a one-line rationale ("process-substitution stderr forwarding caused timing issues in the integration test"), or squash the change into a separate labelled commit so it is discoverable from `git log`.
  - From cursor-specialist-testing-output.txt: add a test assertion (or a comment in the harness) confirming stderr propagation reaches the collector error file after a non-zero collector exit, and add the file to the plan's affected-files list / `relevant-checks.sh` scope to prevent silent regression.
  - From cursor-specialist-plan-fidelity-output.txt: Record this as a separate incidental fix in the plan (or in the PR description); its absence from the plan makes it invisible to completeness reviewers.
  - From cursor-specialist-plan-fidelity-output.txt: Add this file to the plan's file list with a note that the stub update is required to keep the integration test passing under the new gate protocol.



