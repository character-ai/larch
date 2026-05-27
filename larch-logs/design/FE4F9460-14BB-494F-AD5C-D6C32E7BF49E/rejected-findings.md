### [Plan Review] FINDING_7

### FINDING_7: Manual smoke does not exercise parsing with outside ballot
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The manual smoke pairs an outside `--findings-file` with `LARCH_AGGREGATOR_DISABLED=1`, but containment runs before the disabled fast-path, so default-off containment rejects before argv parsing is meaningfully exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pre-smoke with inside-tmpdir only, or require `--allow-findings-outside-tmpdir true` for any outside ballot; optionally add a harness case for disabled+outside+flag


### [Plan Review] FINDING_9

### FINDING_9: Missing edge-case harness coverage
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: Documented edge cases for symlink ballots with `flag=true` and invalid `--allow-findings-outside-tmpdir` values are not covered by the proposed two-case test plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add minimal reject tests: symlink ballot with flag true (existing symlink error, no containment hint); invalid flag value with in-tmpdir ballot (exit 2, `must be true or false`)


### [Plan Review] FINDING_11

### FINDING_11: No auto-staging alternative for outside rewrite blast radius
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The plan does not consider staging merged output before copying back, even though opt-in outside paths plus success `mv -f` can silently corrupt shared round ballots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: For follow-on multi-round work, consider merge-into-tmpdir-then-atomic-copy-back so canonical `round-N/findings-in-scope.md` stays immutable until explicit promotion


