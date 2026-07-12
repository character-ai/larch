---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Pinned tip may diverge from the checked-out tip
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: Refetching `origin/main` after preflight can cause agents to inspect a checkout that differs from the pinned sweep SHA.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Capture and pass the preflight SHA through the workflow, or verify main and origin/main equal the pinned SHA before dispatch and fail closed


### [Plan Review] FINDING_3

### FINDING_3: First-parent enumeration is not explicit
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Without an explicit `--first-parent` Git invocation, enumeration may include side-branch commits that were not on main’s first-parent line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify enumeration as git log --first-parent <watermark>..<pinned-tip> (or equivalent rev-list), keep the same exclusion filters, and add a fixture that would include a side-branch-only commit without --first-parent.


---LARCH-REJECTED-END---
