### FINDING_1: Invalid REPO on internal postplan pause succeeds without pause-save handoff
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `REPO` is invalid during an internal pause checkpoint, `design-postplan-emit.sh` can set `POSTPLAN_EMIT_STATUS=paused`, exit 0, and skip `exec` of `design-pause-save.sh`, while `.pause-requested` may remain. `/design` Step 2b has no handler for that stdout shape (`PAUSE_OK=false` with paused status but no pause-save handoff), so the orchestrator can treat the step as successful and advance past Step 2b into review even though pause was not persisted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: `design-pause-save.sh` drops `.pause-requested` on invalid-repo validation failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On malformed `--repo`, `emit_fail` clears `.pause-requested` before exiting with `PAUSE_OK=false` and exit 0. The pause request is discarded and the run can continue without a pause marker instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_3: Contradictory publish stdout clears valid `RECOVERY_BRANCH` in pause-save
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When publish exits non-zero but stdout still carries `PUBLISH_OK=true` (including a valid `RECOVERY_BRANCH`), pause-save normalization forces `PUBLISH_OK=false` and clears `RECOVERY_BRANCH`. That blocks the resumable recovery pause path even though Gate C / `design-publish` may retain recovery metadata for failed-publish summaries. Operators lose resumable pause recovery for a recoverable failed-publish case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: No integration test for step-5c withheld / resume `STEP` routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After a failed publish the orchestrator can complete step-5b but withhold step-5c; pause-save registry scanning may record the wrong `STEP`, and resume may skip the publish tail. There is no harness asserting `STEP=5c` in pause state when only step-5b completed (e.g. run `design-pause-save.sh` in that configuration).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: `sanitize_publish_metadata` on failed publish paths is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Invalid `PR_URL` in a recovery envelope may be silently stripped on failed publish paths with no CI signal, so operators lose recovery hints. Add a stub case with malformed `PR_URL` and valid `RECOVERY_BRANCH`; assert expected fields in result env and render exports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Clarify failed-publish recovery metadata not visible in Final summary Bash block
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0b clarify documents recovery metadata for failed publish, but the Final summary Bash block only reads prior-shell env vars. `PR_NUMBER` / `RECOVERY_BRANCH` parsed in an earlier fence are not visible to the separate Final summary fence, so `DESIGN_LOG_*` defaults stay empty and failed-publish summaries omit recovery bullets. Persist recovery KVs to a tmpdir env file in the publish subshell, set `DESIGN_LOG_*` in the same fence as `render-final-summary.sh`, or add a two-invocation harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


