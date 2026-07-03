### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:82-106
- **Concern**: Scout-manifest branch still keys only on non-empty RUN_ID. Scenario: The plan gates review log-phase on slug-valid RUN_ID, but the only explicit Step 4 bash block still uses `if [[ -n "${RUN_ID:-}" && "${SCOUT_STATUS:-na}" != "na" ]]`. An implementer can hoist `review_log_root`, guard the bulk opener, capture, and commit, yet still call `review log-phase --batch review-scout-manifest` when RUN_ID contains `/`, `..`, or other slug-invalid bytes. That leaves a partial fix on the exact standalone path this issue targets.
- **Proposed resolution**: Name the scout-manifest guard in ### UPDATED: skills/review/SKILL.md and switch it to the same slug-valid predicate used for bulk log-phase, capture, and commit (not bare non-empty).



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-review-structure.sh:387-388
- **Concern**: Step 4 opener change will break the structural pin without a firm harness update. Scenario: The pin greps for the exact substring `If \`RUN_ID\` is non-empty, write flat review larch-log batches`. The planned RUN_ID slug guard requires replacing that opener with validated-RUN_ID wording, so a correct SKILL.md edit fails `scripts/test-review-structure.sh` unless the pin moves in the same PR. The plan leaves the harness under ### MAY_UPDATE, which treats a required CI companion as optional.
- **Proposed resolution**: Promote `scripts/test-review-structure.sh` to ### UPDATED (or add an explicit cross-reference in the firm SKILL.md section) and update pin (18) to the new validated-RUN_ID opener plus hoisted `review_log_root` contract.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:481-547
- **Concern**: UPDATED helper list omits _capture_design_transcript direct _append_transcript_warning sites. Scenario: The firm plan threads warning_step_label only through _remove_root_transcript, _fetch_claude_source_snapshot, _materialize_claude_source_snapshot, and _refresh_design_source_env. _capture_design_transcript still calls _append_transcript_warning directly for session-id-drift and hoist-failed (lines 481 and 543). Failure-modes grep is advisory; an implementer following only the UPDATED bullets can fix capture-transcript argv and listed helpers yet leave those two paths emitting design Step 5c on pause publish, partially reproducing accepted Finding #1.
- **Proposed resolution**: Add _capture_design_transcript to the UPDATED: design_publish.py contract: pass ctx.warning_step_label (or ctx) into every _append_transcript_warning call inside _capture_design_transcript, not only into the nested helpers.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/SKILL.md:75-77
- **Concern**: Primary Step 4 log-phase prose never shows --log-root on the bulk batch call. Scenario: Line 77 tells classification rounds to reuse the same --run-id and --log-root as other batches, but line 75 describes the main review log-phase write without any --log-root example; only the scout block (102) and capture/commit (111) show review_log_root today. UPDATED says all commands use the hoisted root generically, so an implementer can hoist the variable and fix capture while still omitting --log-root on bulk log-phase calls when LARCH_LOG_ROOT is unset, leaving review batches unstaged even though transcript staging works.
- **Proposed resolution**: In skills/review/SKILL.md UPDATED, require an explicit bulk review log-phase example (or one shared argv template) that includes --log-root "$review_log_root" alongside --run-id, not only scout-manifest and capture/commit fences.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:82-106
- **Concern**: Scout-manifest fence keeps a non-slug `RUN_ID` guard while the plan only removes its inner `review_log_root` assignment. Scenario: Step 1 gates log-phase on slug-valid `RUN_ID`, but the scout jq block still opens with `if [[ -n "${RUN_ID:-}" && "${SCOUT_STATUS:-na}" != "na" ]]`. A non-empty invalid id (for example `foo/bar` or `..`) can still reach `review log-phase` there after bulk batches are skipped
- **Proposed resolution**: Fold the scout block under the same slug-valid `RUN_ID` gate as the other Step 4 log work, or replace the scout `RUN_ID` test with the same slug contract and rely on the hoisted `review_log_root` only



