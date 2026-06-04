Normalized aggregator output from the supplied reviewer findings. Merges are by shared behavioral risk; distinct code paths or fixes stay separate.

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

### FINDING_4: Step 5c gate treats empty `SESSION_ID` like publish success for cleanup semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The step-5c gate treats empty `SESSION_ID` like publish success; with `PUBLISH_OK` unset elsewhere, orchestration can withhold step-5c correctly yet skip cleanup paths that depend on `PUBLISH_OK`, which is confusing. SKILL prose should state that empty `SESSION_ID` is skip-not-failure for `PUBLISH_OK`-dependent gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_7: `assert_clarify_summary_outcome` mirrors SKILL instead of exercising orchestration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness helper duplicates SKILL branching logic rather than testing exported orchestration outcomes. CI can pass while `SKILL.md` clarify sub-step 6 branching is wrong if greps are not updated. Remove the mirror helper or replace with a clarify fixture that asserts exported `SUMMARY_OUTCOME`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: `validate_repo` duplicated across gh entrypoints without shared grammar tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `validate_repo` is copy-pasted across many `gh` entrypoints (clarify, design, pause, log-publish, etc.). A one-line drift in one copy (e.g. weaker `--*` or backslash rejection) could re-open `gh api` path injection via `repos/${REPO}/…` or cross-repo `gh --repo` misuse while other scripts stay strict. Centralize canonical validation (or a shared `validate_gh_repo_slug`) and point malformed-repo tests at that lib.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Clarify failed-publish recovery metadata not visible in Final summary Bash block
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0b clarify documents recovery metadata for failed publish, but the Final summary Bash block only reads prior-shell env vars. `PR_NUMBER` / `RECOVERY_BRANCH` parsed in an earlier fence are not visible to the separate Final summary fence, so `DESIGN_LOG_*` defaults stay empty and failed-publish summaries omit recovery bullets. Persist recovery KVs to a tmpdir env file in the publish subshell, set `DESIGN_LOG_*` in the same fence as `render-final-summary.sh`, or add a two-invocation harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: step-5c completion on publish-skipped runs blocks later publish retry on resume
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: step-5c can be marked complete for publish-skipped runs (empty `SESSION_ID`). If the operator later obtains a `SESSION_ID` and resumes, step-5c already exists so the publish tail is not retried automatically. Withhold step-5c on publish-skipped, add resume logic to re-enter 5c when logs were never flushed, or document publish-skipped as non-resumable for publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Plan wording vs postplan invalid-repo short-circuit before pause-save delegation
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: PLAN_FINDING_2 describes delegating repo handling to `design-pause-save.sh` on internal pause, but invalid resolved repo fails inside postplan with `PAUSE_OK=false` and never execs pause-save. Debugging shows postplan invalid-repo output rather than pause-save invalid-repo. Behavior may match intent but diverges from plan delegation wording; document the short-circuit in `design-postplan-emit.md` or exec pause-save for one canonical invalid-repo path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Intentional asymmetry: pause-save vs `design-publish` on contradictory publish stdout
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pause-save clears `RECOVERY_BRANCH` when normalizing contradictory `PUBLISH_OK=true` on non-zero exit while `design-publish` retains recovery metadata for failed-publish summaries. A publish that exits non-zero yet prints `PUBLISH_OK=true` and valid `RECOVERY_BRANCH` could show recovery hints in the summary but not get a resumable pause marker. Document the intentional asymmetry in `design-pause-save.md`, or preserve `RECOVERY_BRANCH` after sanitizing when stdout contradicted the exit code (overlaps in-scope FINDING_3 as a product/doc choice).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for voters, not machine output):**
- Original FINDING_1, 2, 13 → **FINDING_1** (same postplan invalid-`REPO` / Step 2b gap).
- Original FINDING_4, 11 → **FINDING_3** (same `RECOVERY_BRANCH` clearing on contradictory stdout); kept separate from **FINDING_12** (OOS plan/doc on that asymmetry).
- Original FINDING_9, 10 → **FINDING_8** (`validate_repo` duplication).
- Original FINDING_15 → **FINDING_11**; original FINDING_16 → **FINDING_12** (OOS retained in headings).
- No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).
