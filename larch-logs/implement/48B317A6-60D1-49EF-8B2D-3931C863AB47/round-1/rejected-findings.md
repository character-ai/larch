### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Leaf/state_file non-regular entries are not repaired
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Non-regular leaf or state_file entries are still not proved repairable, so a FIFO or directory leaf can persist stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Seed a directory at the computed state_file path and assert exit 0, no reminder, and no leftover temp files.
  - From codex-specialist-testing: Drop the early exit for movable non-symlink leafs and let the mv path replace them, then add a regression that seeds a FIFO leaf and proves the hook still writes a fresh row.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

