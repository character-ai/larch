### [Plan Review] FINDING_2

### FINDING_2: Plan bundles unrelated cleanup and design workstreams
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Concern**: The plan treats one SIMPLE change as covering two independent workstreams: cleanup enumeration fail-safe behavior and design Step 3 dead-config removal. They touch different runtime surfaces, docs, and harnesses, so a regression in one path can block review or obscure diagnosis of the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Split into separate plans/PRs, or narrow this PR to the live Step 3 regression and leave cleanup for its own minimum-change patch


