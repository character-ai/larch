### [Plan Review] FINDING_4

### FINDING_4: Multiple live markers make clamp ownership ambiguous
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: When more than one live same-clone design-step marker exists, the clamp may attach to the wrong marker or wrong step context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When more than one eligible live dir matches, fail open or deterministically select the dir whose `.bg-wait-active` STEP matches the tightest wait class (prefer the marker whose `tasks/<id>.output` Read is being classified); document and test the multi-marker case instead of silently picking the first `live_dirs_file` row.


### [Plan Review] FINDING_5

### FINDING_5: Clamp must apply before the path gate
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The clamp has to run before the `path_under_dir` gate, or absolute `tasks/*.output` Reads bypass it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: State explicitly in the `hook-bg-poll-guard.sh` plan step that the clamp is a top-level Read branch on tail `tasks/[A-Za-z0-9._-]+.output` when any live same-clone `design-step*` marker exists, before the `path_under_dir` loop, and add a harness Read whose path is outside the tmpdir tree.


