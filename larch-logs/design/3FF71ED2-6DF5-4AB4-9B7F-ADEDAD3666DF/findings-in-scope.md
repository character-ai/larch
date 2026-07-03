### FINDING_1: Scout-manifest RUN_ID guard still allows invalid IDs
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The scout-manifest branch still gates Step 4 review logging on a bare non-empty `RUN_ID` instead of the slug-valid predicate used elsewhere. That means a slug-invalid value can still reach `review log-phase` on the standalone path, leaving a partial fix even if the bulk log-phase, capture, and commit paths are corrected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Name the scout-manifest guard in ### UPDATED: skills/review/SKILL.md and switch it to the same slug-valid predicate used for bulk log-phase, capture, and commit (not bare non-empty).
  - From Cursor-Pragmatic: Fold the scout block under the same slug-valid `RUN_ID` gate as the other Step 4 log work, or replace the scout `RUN_ID` test with the same slug contract and rely on the hoisted `review_log_root` only

### FINDING_2: Step 4 pin needs a matching harness update
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned Step 4 opener wording changes the exact string that `scripts/test-review-structure.sh` pins, so the structural check will fail unless the harness is updated in the same change. Leaving that file under `### MAY_UPDATE` makes a required CI companion look optional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Promote `scripts/test-review-structure.sh` to ### UPDATED (or add an explicit cross-reference in the firm SKILL.md section) and update pin (18) to the new validated-RUN_ID opener plus hoisted `review_log_root` contract.

### FINDING_3: _capture_design_transcript still bypasses warning_step_label
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The updated helper list does not cover the direct `_append_transcript_warning` calls inside `_capture_design_transcript`. That leaves the `session-id-drift` and `hoist-failed` paths emitting the old hardcoded design step label even after the surrounding helper plumbing is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add _capture_design_transcript to the UPDATED: design_publish.py contract: pass ctx.warning_step_label (or ctx) into every _append_transcript_warning call inside _capture_design_transcript, not only into the nested helpers.

### FINDING_4: Bulk Step 4 log-phase example omits hoisted --log-root
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The Step 4 prose still shows `--log-root` only in the scout-manifest and capture/commit examples, not in the bulk review log-phase call. That leaves room for an implementer to hoist the variable but still omit `--log-root` on the main batch path, which can leave review batches unstaged when `LARCH_LOG_ROOT` is unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In skills/review/SKILL.md UPDATED, require an explicit bulk review log-phase example (or one shared argv template) that includes --log-root "$review_log_root" alongside --run-id, not only scout-manifest and capture/commit fences.
