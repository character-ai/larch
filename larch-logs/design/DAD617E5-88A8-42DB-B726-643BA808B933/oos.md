### FINDING_3: [OUT_OF_SCOPE] README catalog blurb still lags the merit gate
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: The README `--oos` blurb still mentions actuality-only discard behavior and omits the merit gate, so the catalog will keep drifting from the updated skill description until a separate sync lands.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### FINDING_4: [OUT_OF_SCOPE] Rejected-items display should show source keys on collisions
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: Showing bare keys in the `Rejected items (merit)` list can collide across sources; proactively showing `#source/key` would reduce ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### FINDING_5: [OUT_OF_SCOPE] Frontmatter description still needs a char-budgeted draft
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: The frontmatter `description:` follow-up can still use a candidate string with a char-budget note; the failure mode and lint commands are enough for implementation.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

