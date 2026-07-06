### [Plan Review] FINDING_4

### FINDING_4: Promote-release path points at the wrong module
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: minor
- **Concern**: The MAY_UPDATE entry targets a nonexistent `python/larch/issue/promote_release.py`, leaving the real release-promotion gh callsites outside the intended audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Repoint the MAY_UPDATE entry to `python/larch/release/promote_release.py` and keep the dynamic-argv baseline note there.
  - From Cursor-Innovation: Fix the MAY_UPDATE path to python/larch/release/promote_release.py and note proc.run gh literals there need gh-wrapper migration or a subprocess-via-runner-gh baseline row


