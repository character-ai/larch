### [Plan Review] FINDING_3

### FINDING_3: SessionStart drift probe may add unnecessary hook surface
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: Adding the drift probe and shared sparse-dir library expands the SessionStart hook with extra sourcing and git sparse-checkout comparison logic for a condition already repaired by `/upgrade-larch`, increasing runtime hook risk and test/docs churn beyond the release/upgrade fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Limit this PR to RC1 and RC2: keep the allowlist in upgrade-larch.sh unless another required runtime consumer remains, drop the SessionStart drift probe and its related docs/tests/agent-lint plumbing, and rely on /upgrade-larch reconcile-on-drift for repair


