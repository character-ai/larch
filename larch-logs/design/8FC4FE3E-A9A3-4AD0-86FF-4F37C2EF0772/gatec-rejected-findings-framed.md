---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_3

### FINDING_3: #6591 correcting comment should cite both #6580 and #6595 fixes
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The planned issue-comment body for correcting #6591’s disposition cites only the stable `LARCH_CLAUDE_PID` launcher path (#6580). Issue scope requires recording that the harness-kill false-orphan root cause was fixed via both #6580 and #6595 (daemon owner-validation hardening). Omitting #6595 leaves the comment incomplete relative to the stated root-cause narrative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: The comment body should state Step 3 is covered by stable `LARCH_CLAUDE_PID` ownership (#6580) and daemon owner-validation hardening (#6595), with both pinned by the new regression tests (or cite existing daemon tests if unchanged).


---LARCH-REJECTED-END---
