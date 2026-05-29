### [Plan Review] FINDING_10

### FINDING_10: Legacy identity fallback tests do not cover all resolver arms
- **Reviewer(s)**: Cursor-dyn-identity-transition, Codex-dyn-identity-transition
- **Severity**: important
- **Concern**: A single legacy `.larch-keepalive` fixture may miss resolver bugs across the distinct eligibility arms for `design-export/manifest.env`, `review-round-summary.md`, and `.bump-version-armed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-identity-transition: Revise the test step to exercise legacy .larch-keepalive binding for each resolver arm, preferably by parameterizing the existing SessionStart fixture helper rather than adding broad new harnesses.


### [Plan Review] FINDING_12

### FINDING_12: Temporary legacy fallback has no removal trigger
- **Reviewer(s)**: Cursor-dyn-identity-transition, Codex-dyn-identity-transition
- **Severity**: latent
- **Concern**: The planned read-only `.larch-keepalive` compatibility fallback has no expiry or removal condition, so it may become permanent compatibility code and hide future `.larch-session` regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-identity-transition: Update the planned resolver doc/comment to name a concrete removal trigger, such as after one release window or after no supported in-flight sessions can predate this rollout.

