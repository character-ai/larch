### [Plan Review] FINDING_5

### FINDING_5: Tally SCOPE_ANCHOR_FILE passthrough is unnecessary and misleading
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Adding `--scope-anchor-file` / `SCOPE_ANCHOR_FILE` passthrough to tally expands argv, tests, and docs even though tally only scores ballots and does not render or consume scope-anchor prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Drop tally `--scope-anchor-file` / `SCOPE_ANCHOR_FILE` emission from item 2. Keep anchor threading in the loop and Step 3 env layers only.


