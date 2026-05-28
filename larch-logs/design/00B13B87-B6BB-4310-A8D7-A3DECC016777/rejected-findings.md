### [Plan Review] FINDING_7

### FINDING_7: Stale-round cleanup uses unchecked rm -rf path
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: Proposed cleanup deletes `"$DESIGN_TMPDIR/plan-review/round-"*` without first validating that `plan-review` is a safe directory under the session tree. A symlink or swapped path could cause deletion outside the intended tempdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Before cleanup, reject symlink/non-directory plan-review paths, resolve the physical root, and delete only validated child directories under that root


### [Plan Review] FINDING_14

### FINDING_14: New loop KVs are parsed but not behaviorally specified
- **Reviewer(s)**: Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync
- **Severity**: important
- **Concern**: The plan emits and documents `IMPORTANT_ACCEPTED_COUNT`, `CONVERGENCE_STREAK`, and `REASON`, but SKILL.md only promises parsing and branches primarily on `LOOP_STATUS`. Gate B behavior and warning text cannot reliably use these fields without a defined branch matrix and validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync: Add an explicit SKILL.md branch matrix for LOOP_STATUS plus REASON, IMPORTANT_ACCEPTED_COUNT, and CONVERGENCE_STREAK. Include the keys in the Bash case parser, initialize them, validate expected enum/range values, and define how each affects Gate B mode and warning text.


### [Plan Review] FINDING_17

### FINDING_17: findings-classification.tsv contract is ambiguous
- **Reviewer(s)**: Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract
- **Severity**: important
- **Concern**: `findings-classification.tsv` is described both as a canonical loop snapshot artifact and as a publish-only back-compat superset item. The loop and publish allowlists can diverge because the intended ownership is unclear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract: Choose and document one contract: either findings-classification.tsv remains a canonical loop-produced artifact, or it is legacy publish-only; update the loop allowlist, publish allowlist, docs, and golden fixtures to make that asymmetry explicit


