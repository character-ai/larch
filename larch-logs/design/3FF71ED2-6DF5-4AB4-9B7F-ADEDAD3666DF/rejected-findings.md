### [Plan Review] FINDING_2

### FINDING_2: Step 4 pin needs a matching harness update
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned Step 4 opener wording changes the exact string that `scripts/test-review-structure.sh` pins, so the structural check will fail unless the harness is updated in the same change. Leaving that file under `### MAY_UPDATE` makes a required CI companion look optional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Promote `scripts/test-review-structure.sh` to ### UPDATED (or add an explicit cross-reference in the firm SKILL.md section) and update pin (18) to the new validated-RUN_ID opener plus hoisted `review_log_root` contract.


### [Plan Review] FINDING_4

### FINDING_4: Bulk Step 4 log-phase example omits hoisted --log-root
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The Step 4 prose still shows `--log-root` only in the scout-manifest and capture/commit examples, not in the bulk review log-phase call. That leaves room for an implementer to hoist the variable but still omit `--log-root` on the main batch path, which can leave review batches unstaged when `LARCH_LOG_ROOT` is unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In skills/review/SKILL.md UPDATED, require an explicit bulk review log-phase example (or one shared argv template) that includes --log-root "$review_log_root" alongside --run-id, not only scout-manifest and capture/commit fences.


