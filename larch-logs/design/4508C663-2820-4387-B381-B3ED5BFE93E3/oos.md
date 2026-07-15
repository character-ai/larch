### FINDING_4: Verify unprefixed stale references
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Prefix-filtered enumeration does not detect dead unprefixed machinery names, so stale `*.sh` references in `SECURITY.md` could remain while both acceptance checks pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit verification step outside the prefix filter: review or mechanically check bare `*.sh` and other unprefixed machinery citations called out in the SECURITY.md sweep bullets, and require each to be repointed, rewritten, or documented with a PR deletion rationale.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

