### [Plan Review] FINDING_1

### FINDING_1: Clarify structural assertion anchors on wrong sub-step
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 0b clarify structural assertion is planned around a non-existent or wrong “sub-step 3.5” anchor, which could miss the intended clarify publish/rename contract or match the wrong Gate B section instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin the assertion to ordering between the line-463 publish bullet (non-zero _publish_rc forces PUBLISH_OK=false) and the line-465 rename gate (SESSION_ID non-empty and PUBLISH_OK=true); drop "sub-step 3.5" from the grep anchor and align plan/test-design-structure.md wording with clarify sub-step 5


