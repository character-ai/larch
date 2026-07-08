---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_4

### FINDING_4: Missing ship pre-driver test module is misclassified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The plan points to a test module that does not exist, so the pre-driver coverage cases have no real home.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Change the heading to ### NEW: if splitting tests, or ### UPDATED: python/tests/implement/test_implement_dispatch.py if extending the existing pre-driver tests there. Keep the acceptance cases either way.


### [Plan Review] FINDING_5

### FINDING_5: Missing self-review test module is misclassified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The plan points to a self-review test module that does not exist, so the forced self-review case has no real home.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Change the heading to ### NEW: python/tests/implement/test_implement_self_review.py, or fold the forced self-review case into an existing Step 5 self-review test module and update that UPDATED path instead.


### [Plan Review] FINDING_9

### FINDING_9: Step 2 docs still forbid branching on coverage disposition
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The Step 2 stdout contract still says coverage KVs are advisory and must not drive branching, which conflicts with the new disposition gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Update step2-dispatch.md in the firm file list: document new coverage KVs, disposition-required semantics, and that Step 2 now branches on disposition-required output


---LARCH-REJECTED-END---
