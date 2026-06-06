### [Plan Review] FINDING_4

### FINDING_4: Makefile registration may duplicate #3548 wiring
- **Reviewer(s)**: Codex-dyn-dependency-verify-first
- **Severity**: latent
- **Concern**: The Makefile registration for test-check-scope-reduction-marker is described as net-new even though PR #3548 may already own the .PHONY, shard prerequisite, and recipe wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-dependency-verify-first: Revise the Makefile item to verify-first/no-op when test-check-scope-reduction-marker is already in .PHONY, a harness shard, and has the existing recipe; only add missing wiring if one of those surfaces is absent


