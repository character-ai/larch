---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_6

### FINDING_6: Pre-ship checks repair loops still route failures to main-agent edits
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The plan leaves the Step 3, Step 5, and Step 6 repair loops unchanged, including paths that return `NEXT_ACTION=main-agent-edit` after delegated dispatch failure, head changes, or iteration exhaustion. This leaves the required inline-fallback removal incomplete because vendor timeout or failure can still route repair back to main-agent edits instead of continuing through the delegated waterfall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify and implement the required pre-ship retry routing, including fresh next-tier dispatch and bounded exhaustion handling, then update the affected checks-loop contract and focused tests


---LARCH-REJECTED-END---
