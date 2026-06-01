### [Plan Review] FINDING_5

### FINDING_5: REPO fallback resolution moved before plan-block-write
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-publish-ordering
- **Severity**: latent
- **Concern**: Plan moves fallback `REPO` resolution before `plan-block-write` even though current Step 5c resolves only after a successful plan write and explicitly skips resolution on plan-write failure. This adds an unnecessary resolve-repo/gh call before the critical publish mutation and drifts from pure extraction / minimum-change ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Keep only caller-provided REPO before plan-block-write; perform fallback resolve after plan-block-write succeeds, and render failed-plan-write summary with existing/provided REPO or no repo
  - From Codex-dyn-publish-ordering: Keep only caller-provided REPO before plan-block-write; perform fallback resolve after plan-block-write succeeds, and render failed-plan-write summary with existing/provided REPO or no repo


