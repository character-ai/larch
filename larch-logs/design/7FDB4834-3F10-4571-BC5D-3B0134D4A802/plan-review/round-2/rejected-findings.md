### [Plan Review] FINDING_2

### FINDING_2: Python `oos-filing` path can bypass mandatory OOS pipeline load
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Concern**: The Python implementation’s `needs_user_reason=oos-filing` path can dispatch into the existing Step 9a.1 flow while `OOS_PENDING` is still false, without loading the restored canonical `oos-pipeline.md` procedure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the same mandatory read directive to the oos-filing dispatch clause, or explicitly route that clause through the OOS checkpoint/pipeline block before invoking /issue


