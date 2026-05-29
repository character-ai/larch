### [Plan Review] FINDING_3

### FINDING_3: Script sibling docs still describe Family B / paired-PID
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Concern**: Several script sibling markdown files still describe Family B writers and paired-PID Stage 3 contracts that the plan does not list for update (`run-step5-review.md`, `collect-agent-results.md`, `dispatch-plan-voters.md`, `ci-wait.md`, `ship-pr.md`). After removing the Family B fence and shim layer, shipped docs could contradict runtime behavior; the script-md sibling rule expects behavior docs to move with contract changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add these sibling docs to the UPDATED set and delete or restate only the stale Family B paired-PID sentences without broader rewrites

