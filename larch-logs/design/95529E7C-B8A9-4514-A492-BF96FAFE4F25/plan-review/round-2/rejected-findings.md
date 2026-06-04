### [Plan Review] FINDING_3

### FINDING_3: Publish-tail docs retain stale ordering
- **Reviewer(s)**: Codex-dyn-publish-state-machine
- **Severity**: latent
- **Concern**: The plan updates publish docs for new outcomes but leaves stale ordering text that contradicts the current driver and harness, implying pre-publish render and reentry marker behavior that no longer match the actual gated publish sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publish-state-machine: Extend the design-publish.md and render-final-summary.md doc edits to state the actual order: plan write, diagram upsert, design-log-publish, post-publish render, [DESIGNED] rename, then reentry marker; no pre-publish render; rename and marker gated on non-empty SESSION_ID and PUBLISH_OK=true.


