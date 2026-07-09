---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Omission suffix should ignore filtered validation todos
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The omission marker can be emitted for filtered-out validation todos even when there are no omitted blocking items, which breaks the intended empty `todos_left` contract and pollutes downstream artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Compute omission counts from blocking items only (`len(blocking_items) > len(displayed_blocking_lines)`), never from raw-vs-filtered deltas; keep nonblocking ignores silent


### [Plan Review] FINDING_3

### FINDING_3: Stale-fingerprint check should not block when no disposition is required
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: `validate_disposition_for_ship` appears to reject advisory cases on fingerprint staleness before confirming that no disposition is required, which can halt ship flow even when the recomputed state no longer needs operator choice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: When disposition_required is false after recompute, return ok before stale enforcement, or unlink stale disposition records in that branch; add a unit test with a recorded proceed-partial plus a benign-only manifest under advisory coverage


---LARCH-REJECTED-END---
