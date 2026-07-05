### FINDING_4: Add an explicit regression for `&` segment restarts
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Concern**: The planned regression coverage mentions `||`, `&&`, `;`, pipelines, and `|&`, but not a standalone `&` boundary, so a bad background-separator restart could still go untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add one allowed/flagged pair, e.g. flag `sleep 1 & rg PATTERN ../root` and keep a safe no-path `sleep 1 & true` or similar non-grep control if needed


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

