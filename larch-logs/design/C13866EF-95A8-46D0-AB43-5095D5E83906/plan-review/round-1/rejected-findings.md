### [Plan Review] FINDING_5

### FINDING_5: paired-PID env var cleanup docs left stale
- **Reviewer(s)**: Cursor-dyn-env-var-scope, Codex-dyn-env-var-scope
- **Severity**: latent
- **Concern**: The plan removes parent `LARCH_PAIRED_PID_FILE` barriers but leaves docs saying `ci-wait.sh` is protected because `ship-pr.sh` unsets that env var. Future readers may preserve or reintroduce dead paired-PID plumbing based on stale documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-env-var-scope/Codex-dyn-env-var-scope: Add these references to the Stage 3 doc cleanup, or explicitly mark them as Stage-4-deferred skill-fence prose in the plan

