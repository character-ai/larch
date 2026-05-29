### FINDING_1: Avoidable standalone rebase-push fetch harness
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: nit
- **Concern**: The new standalone rebase-push fetch harness expands SIMPLE-tier maintenance surface for a narrow fetch-retry assertion that can be covered by the existing keep-on-conflict harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Extend scripts/test-rebase-push-keep-on-conflict.sh with the transient-once and persistent-fetch-failure cases, update its sibling md, and drop the NEW harness plus Makefile and agent-lint additions

### FINDING_2: Missing adversarial negatives for broad network signatures
- **Reviewer(s)**: Cursor-dyn-predicate-scope-drift, Codex-dyn-predicate-scope-drift
- **Severity**: latent
- **Concern**: Planned signature coverage adds only positive cases for broad DNS/reset entries, leaving near-miss strings unpinned and allowing substring-based matching to misclassify adjacent non-network output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-predicate-scope-drift, Codex-dyn-predicate-scope-drift: Add targeted negative fixtures beside the new positives for lookup/no such host/Connection reset by peer, especially a lowercase no such hosted near-miss and a lookup line without resolver/no such host shape; narrow the bare no such host pattern if the negative exposes overmatch.
