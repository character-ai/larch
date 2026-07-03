### FINDING_1: Scout-manifest RUN_ID guard still allows invalid IDs
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The scout-manifest branch still gates Step 4 review logging on a bare non-empty `RUN_ID` instead of the slug-valid predicate used elsewhere. That means a slug-invalid value can still reach `review log-phase` on the standalone path, leaving a partial fix even if the bulk log-phase, capture, and commit paths are corrected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Name the scout-manifest guard in ### UPDATED: skills/review/SKILL.md and switch it to the same slug-valid predicate used for bulk log-phase, capture, and commit (not bare non-empty).
  - From Cursor-Pragmatic: Fold the scout block under the same slug-valid `RUN_ID` gate as the other Step 4 log work, or replace the scout `RUN_ID` test with the same slug contract and rely on the hoisted `review_log_root` only


### FINDING_3: _capture_design_transcript still bypasses warning_step_label
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The updated helper list does not cover the direct `_append_transcript_warning` calls inside `_capture_design_transcript`. That leaves the `session-id-drift` and `hoist-failed` paths emitting the old hardcoded design step label even after the surrounding helper plumbing is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add _capture_design_transcript to the UPDATED: design_publish.py contract: pass ctx.warning_step_label (or ctx) into every _append_transcript_warning call inside _capture_design_transcript, not only into the nested helpers.


