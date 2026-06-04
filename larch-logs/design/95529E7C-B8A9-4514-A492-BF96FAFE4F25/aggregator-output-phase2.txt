### FINDING_1: Clarify sub-step 6 overwrites failed-publish with cancelled-clarify
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-resume-state
- **Severity**: important
- **Concern**: Step 0b clarify adds fail-closed publish parsing and `DESIGN_LOG_*` recovery in sub-step 3, but sub-step 6 still unconditionally exports `SUMMARY_OUTCOME=cancelled-clarify` before the Final summary block. After a failed clarify publish (`SESSION_ID` non-empty and `PUBLISH_OK` not true), the summary path stays cancelled-clarify instead of `failed-publish`, so `render-final-summary.sh` does not apply failed-publish recovery behavior (recovery bullets, suppressed run-log advertising) and can still expose a successful-looking run-log path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Revise item 6 so SUMMARY_OUTCOME is failed-publish when SESSION_ID is non-empty and PUBLISH_OK is not true, otherwise cancelled-clarify; keep DESIGN_LOG_PR_NUMBER, DESIGN_LOG_PR_URL, and DESIGN_LOG_RECOVERY_BRANCH set before the Final summary block
  - From Codex-Innovation: Revise item 6 so SUMMARY_OUTCOME is failed-publish when SESSION_ID is non-empty and PUBLISH_OK is not true, otherwise cancelled-clarify; keep DESIGN_LOG_PR_NUMBER, DESIGN_LOG_PR_URL, and DESIGN_LOG_RECOVERY_BRANCH set before the Final summary block
  - From Cursor-Edge: In Step 0b sub-step 6, branch SUMMARY_OUTCOME: use failed-publish when SESSION_ID was non-empty and normalized PUBLISH_OK is not true; keep cancelled-clarify only on the successful clarify path. Export DESIGN_LOG_* before the Final summary block as the plan already requires.
  - From Cursor-Innovation: Update clarify loop item 6 to export SUMMARY_OUTCOME=failed-publish when SESSION_ID is non-empty and PUBLISH_OK!=true (else cancelled-clarify) immediately before the Final summary block; pin item 6 conditional wording in test-design-structure.sh not only sub-step 3 publish prose
  - From Cursor-Pragmatic: In sub-step 6, choose failed-publish when SESSION_ID is non-empty and PUBLISH_OK is not true after sub-step 3; keep cancelled-clarify only when publish was skipped or succeeded; add a structural grep on that sub-step 6 branch in scripts/test-design-structure.sh
  - From Cursor-Requirements: In sub-step 6, choose failed-publish when SESSION_ID is non-empty and PUBLISH_OK is not true after sub-step 3; keep cancelled-clarify only when publish was skipped or succeeded; add a structural grep on that sub-step 6 branch in scripts/test-design-structure.sh
  - From Cursor-dyn-resume-state: In sub-step 6, branch before the Final summary block: when SESSION_ID is non-empty and PUBLISH_OK != true after sub-step 3 normalization, export DESIGN_LOG_PR_NUMBER/URL/RECOVERY_BRANCH and set SUMMARY_OUTCOME=failed-publish; keep cancelled-clarify only when publish was skipped or succeeded

### FINDING_2: design-postplan-emit internal pause path omits --repo
- **Reviewer(s)**: Codex-Edge, Codex-dyn-resume-state
- **Severity**: important
- **Concern**: The plan forwards `--repo` in prompt-side pause checks, but `design-postplan-emit.sh` can still see `.pause-requested` during internal Step 2b and exec `design-pause-save.sh` without `--repo`. Non-default-repo runs can then target the gh default hub for pause publish, issue-body read, marker writes, and recovery metadata; pause-save validation on direct calls does not cover this path because the intended repo is never passed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Keep the change surgical: append ${REPO:+--repo "$REPO"} to this exec path and add/adjust the design-postplan-emit pause test or contract so this callsite is covered by the same repo-forwarding assertion
  - From Codex-dyn-resume-state: Add a minimum repo-forwarding path for design-postplan-emit.sh: parse optional --repo or safely read export REPO from source-env.sh, validate OWNER/REPO, and pass ${REPO:+--repo "$REPO"} to design-pause-save.sh. Update the Step 2b/Gate re-emit call sites and test-design-postplan-emit.sh pause case to assert --repo is forwarded.

### FINDING_3: render-run-summary rebuilds run-log path for failed-publish with real RUN_ID
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-summary-ops
- **Severity**: important
- **Concern**: The plan relies on `RUN_LOGS_PATH=N/A` from `render-final-summary.sh` for `failed-publish`, but `render-run-summary.sh` fallback only suppresses synthesis when `RUN_ID=unknown`. For failed-publish with a real session/run id, the shared renderer can still replace `N/A` with `larch-logs/design/<run-id>/`, advertising logs that did not publish; primary and fallback summaries can disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Extend the proposed guard to also skip fallback for failed-publish, and add a real-run-id failed-publish test alongside the unknown-run-id case
  - From Codex-dyn-summary-ops: Extend the render-run-summary fallback guard to skip synthesis for failed-publish as well as RUN_ID=unknown, and add render-run-summary plus render-final-summary primary/fallback tests asserting failed-publish Run logs stays N/A while approved real-run-id still renders the path.

### FINDING_4: design-pause-save --repo validation bypassed via source-env overwrite
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Validating the effective `REPO` only after sourcing `source-env.sh` allows `source-env.sh` to overwrite a malformed argv `--repo` before validation. A direct call with `--repo /abs` plus a `source-env.sh` that exports a valid `REPO=owner/repo` could pass post-source validation and reach gh/state work, violating the fail-closed direct `--repo` requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Preserve the parsed argv repo before sourcing and validate it immediately, or restore argv precedence after sourcing; add the malformed --repo regression with source-env.sh also exporting a valid REPO so the bypass is covered

### FINDING_5: pause --repo not persisted into current-design-env
- **Reviewer(s)**: Codex-dyn-envelope-contracts
- **Severity**: important
- **Concern**: Planned pause `--repo` forwarding in SKILL preludes is not persisted when `design-init-runparams.sh` calls `write-design-current-env.sh` without forwarding `--repo`. Later Bash blocks that only source `current-design-env` still see unset `REPO`, so non-default-repo pauses can fall back to hub/default repo even after prompt-side `${REPO:+--repo "$REPO"}` additions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-envelope-contracts: Append [[ -n "$REPO" ]] && _wdce_args+=(--repo "$REPO") in design-init-runparams.sh before invoking write-design-current-env.sh, and add a structural/test pin that source-env/current-design-env includes REPO for non-default repo runs.

### FINDING_6: publish-skipped omits Outcome bullet in summary renderers
- **Reviewer(s)**: Cursor-dyn-summary-ops
- **Severity**: important
- **Concern**: The plan adds publish-skipped handling but primary and `compose_self_fallback` paths in `render-run-summary.sh` / `render-final-summary.sh` only emit `- **Outcome**` for bailed/stalled/cancelled/failed patterns. `publish-skipped` is grouped with approved-style outcomes (no Outcome bullet), so operators scanning bullets can treat it like success; the planned `test-render-final-summary.sh` matrix expects an explicit Outcome line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-summary-ops: Add publish-skipped to the Outcome case in scripts/render-run-summary.sh and skills/design/scripts/render-final-summary.sh compose_self_fallback (395); keep the planned Publish skipped note as additive
