### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:241-255
- **Concern**: [SCOPE-REDUCTION] Proposed final-mode idempotent success check treats any existing default-branch run-log tree as proof that final publish already completed. Scenario: A pause save uses scripts/design-pause-save.sh to publish the same larch-logs/design/$RUN_ID tree with --reason pause. After resume, final Step 5c would see that pause tree on origin/<default>, emit PUBLISH_OK=true before staging current final artifacts, and skip the required final log publish.
- **Proposed resolution**: Do not return success from a pre-worktree ls-tree path-exists probe alone. Keep final idempotency on the existing post-staging empty-porcelain path, or require proof that cannot be produced by pause before short-circuiting. Add a pause-publish then final-publish regression.
