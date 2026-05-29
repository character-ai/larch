### FINDING_2: Final summary block references retired tier-flag mutual-exclusion abort
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: The Final summary block “When” clause at `skills/design/SKILL.md:354` still names a tier-flag mutual-exclusion abort. After removing `--simple` and duplicate-tier mutual exclusion, implementers updating the `SUMMARY_OUTCOME` enum in the same section can leave this pre-`DESIGN_TMPDIR` skip label pointing at a retired exit path; the surviving equivalent is disallowed-public-argv abort before Step 0 (no `DESIGN_TMPDIR`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a plan bullet under skills/design/SKILL.md Final summary block: replace tier-flag mutual-exclusion abort with disallowed public argv abort before Step 0 (no DESIGN_TMPDIR)

