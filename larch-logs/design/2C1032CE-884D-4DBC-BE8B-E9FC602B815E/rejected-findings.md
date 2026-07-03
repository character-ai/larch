### [Plan Review] FINDING_1

### FINDING_1: Step 3 reruns still suppress fresh Gate B timing rows
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan leaves the Step 3 re-entry timing defect unresolved. On rerun of the same design round, the existing round row and fixed `gate-b-apply-round-N.out` row can cause the timing helpers to return early, so the rerun still gets no fresh round window and no second `gate-b/apply` span.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the narrow rerun remedy to the plan, such as attempt-specific design round timing plus attempt-specific Gate B output basenames, or split that Important issue item out before landing this narrower PR.
  - From Codex-Pragmatic: Add the narrow rerun handling requested by the issue: reset or version the design round and gate-b apply timing per attempt on Step 3 re-entry, or split that Important item into a separate tracked issue before landing this narrower PR.
  - From Codex-Requirements: Add one stated rerun remedy to the plan: per-attempt design round rows with attempt-specific Gate B output basenames, or a safe Step 3 re-entry cleanup of prior same-round Gate B timing rows.

