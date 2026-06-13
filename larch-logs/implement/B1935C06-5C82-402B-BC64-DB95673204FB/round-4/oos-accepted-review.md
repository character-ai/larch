### OOS_2: [OUT_OF_SCOPE] Publish-tail abort mixes final-summary prose into Step 5c KV stdout
- **Reviewer(s)**: dyn-design-reporting-output.txt
- **Severity**: latent
- **Concern**: `design-step5c.sh` calls `render-final-summary.sh` uncaptured on publish-tail abort, so final-summary prose can mix into Step 5c stdout on that path. This is a separate KV-channel concern from the publish `>/dev/null` sidecar visibility issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-reporting-output.txt: (No separate fix proposed beyond identifying the KV-channel concern.)


