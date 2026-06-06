### [Plan Review] FINDING_4

### FINDING_4: Drift baseline parsing lacks invalid-value safeguards
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: A malformed or partially written `drift-baseline.env` can leave missing or non-numeric `BASELINE_*` values; arithmetic under `set -e` may then crash Step 2b.5 instead of treating drift as false/no-baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Specify non-negative integer validation for both baseline keys before arithmetic and treat invalid or incomplete baseline files like absent baseline; preferably write drift-baseline.env via an atomic temp+mv helper that refuses symlink targets


