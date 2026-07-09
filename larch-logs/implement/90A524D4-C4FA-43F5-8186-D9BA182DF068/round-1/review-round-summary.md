# Review Round 1

- Mode: `diff`
- 1 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_6: Marker write follows symlinks
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Writing the missing-guideline marker through a normal path write can follow a symlink and truncate an arbitrary same-UID writable file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


