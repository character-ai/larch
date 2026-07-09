### FINDING_4: Step 3 wrapper cleanup must keep result-env hygiene
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The step-3 review wrapper is being changed as if all stale result-env cleanup should go away, but the fresh-launch result-env reset is required hygiene and must remain distinct from removing the sentinel path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `design-step3-review.sh` instructions, explicitly **keep** the fresh-launch `rm -f "$DESIGN_TMPDIR/bgjob/design-step3-review.result.env"` (and equivalent merge-env hygiene) while removing only `.completed/step-3-terminal`, `.step3-terminal-persisted-this-run`, and `--sentinel`.


### FINDING_5: Clone-ownership parity harness needs an explicit fate
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The plan removes the hooks that the clone-ownership parity harness checks but leaves the harness and live Make target in place, so CI will either call a deleted script or keep testing a dead contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Pick a concrete disposition: drop the target and harness from Makefile/shards, or rewrite the harness around a surviving contract and update its docs


### FINDING_8: Pre-commit still invokes deleted writer-parity lint
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The pre-commit configuration still invokes the writer-parity lint that the plan deletes, so `make lint` will keep calling a removed command unless the hook entry is removed with the code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add `### UPDATED: .pre-commit-config.yaml` to remove the `lint-bg-wait-writer-parity` hook while keeping `lint-bg-wait-coverage`.


### FINDING_9: Shared final-summary emit still contains task-notification
- **Reviewer(s)**: Cursor-dyn-Workflow Contract Auditor
- **Severity**: major
- **Concern**: A shared skills rule still contains the forbidden `task-notification` token, so the extinct-token acceptance grep will keep finding the old wait mechanism even after the surrounding harnesses are removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Workflow Contract Auditor: Add `### UPDATED: skills/shared/final-summary-emit.md` to rephrase the forbidden-source rule without the literal `task-notification` token (for example “not background-task notification output”), or add the file to the enumerated survivor list with justification.


### FINDING_1: Stale anti-polling companion doc pins retired literals
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The companion markdown for the deleted anti-polling harness still pins retired literals (`design-background-wait`, `task-notification`, and other removed contracts). After `scripts/test-implement-anti-polling-rule.sh` is deleted, that stale doc can keep the plan’s extinct-token grep failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Delete this companion doc with the harness, or rewrite it to describe only the bgjob-wait replacement contract


