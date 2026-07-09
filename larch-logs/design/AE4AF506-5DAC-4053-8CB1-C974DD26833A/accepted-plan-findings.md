### FINDING_3: Baseline keying should include match context
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The baseline record does not pin the match-position context, so distinct hits on the same line can collapse into one identity and collide in occurrence, suppression, and write-shrink behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `context` to the typed baseline record and to `Finding.key()` (e.g. `startswith`, `compare_eq`, `regex_pattern`, `membership_in`), mirroring sibling ratchets that pin `access`/`callee`


