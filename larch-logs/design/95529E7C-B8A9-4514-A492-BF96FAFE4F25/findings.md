### FINDING_1:
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:463-466
- **Concern**: Step 0b clarify publish fix conflicts with the later unconditional cancelled-clarify summary instruction. Scenario: The plan says failed clarify publishes should render failed-publish and suppress successful run-log advertising, but item 6 still unconditionally exports SUMMARY_OUTCOME=cancelled-clarify before the Final summary block; a failed clarify publish can still produce the old honest-summary bug
- **Proposed resolution**: Revise item 6 so SUMMARY_OUTCOME is failed-publish when SESSION_ID is non-empty and PUBLISH_OK is not true, otherwise cancelled-clarify; keep DESIGN_LOG_PR_NUMBER, DESIGN_LOG_PR_URL, and DESIGN_LOG_RECOVERY_BRANCH set before the Final summary block

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:466
- **Concern**: Step 0b clarify sub-step 6 still hard-exports SUMMARY_OUTCOME=cancelled-clarify. Scenario: Plan sub-step 3 adds fail-closed publish parsing and says to render failed-publish with DESIGN_LOG_* and suppressed run logs on failed publish, but sub-step 6 still unconditionally exports cancelled-clarify before the Final summary block. render-final-summary.sh sets RUN_LOGS_PATH to larch-logs/design/<RUN_ID>/ whenever OUTCOME is not failed-publish and RUN_ID is set (render-final-summary.sh:295-298), so a failed clarify publish can still advertise a successful run-log path and skip failed-publish recovery notes.
- **Proposed resolution**: In Step 0b sub-step 6, branch SUMMARY_OUTCOME: use failed-publish when SESSION_ID was non-empty and normalized PUBLISH_OK is not true; keep cancelled-clarify only on the successful clarify path. Export DESIGN_LOG_* before the Final summary block as the plan already requires.

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-postplan-emit.sh:157-167
- **Concern**: Pause repo forwarding misses the driver-internal pause checkpoint. Scenario: The plan updates SKILL.md pause preludes but design-postplan-emit.sh can still see .pause-requested during its internal Step 2b work and exec design-pause-save.sh without --repo, so non-default repo runs can fall back to the hub default before gh issue view, publish, or marker writes
- **Proposed resolution**: Keep the change surgical: append ${REPO:+--repo "$REPO"} to this exec path and add/adjust the design-postplan-emit pause test or contract so this callsite is covered by the same repo-forwarding assertion

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:463-466
- **Concern**: Clarify failed-publish routing stops at sub-step 3 prose while item 6 still exports SUMMARY_OUTCOME=cancelled-clarify unconditionally. Scenario: After a non-zero clarify publish (or PUBLISH_OK!=true) sub-step 3 may normalize failure and set DESIGN_LOG_* but item 6 always runs the Final summary block as cancelled-clarify so render-final-summary.sh keeps RUN_LOGS_PATH=larch-logs/design/<SESSION_ID>/ and omits append_failed_publish_notes recovery bullets
- **Proposed resolution**: Update clarify loop item 6 to export SUMMARY_OUTCOME=failed-publish when SESSION_ID is non-empty and PUBLISH_OK!=true (else cancelled-clarify) immediately before the Final summary block; pin item 6 conditional wording in test-design-structure.sh not only sub-step 3 publish prose

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:466
- **Concern**: Step 0b clarify sub-step 6 still unconditionally exports SUMMARY_OUTCOME=cancelled-clarify before the Final summary block. Scenario: After sub-step 3 normalizes a failed publish to PUBLISH_OK=false and sets DESIGN_LOG_* recovery metadata, sub-step 6 overwrites the intended failed-publish summary with cancelled-clarify, so recovery bullets and suppressed-run-log behavior never reach render-final-summary.sh
- **Proposed resolution**: In sub-step 6, choose failed-publish when SESSION_ID is non-empty and PUBLISH_OK is not true after sub-step 3; keep cancelled-clarify only when publish was skipped or succeeded; add a structural grep on that sub-step 6 branch in scripts/test-design-structure.sh

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:221-224
- **Concern**: Planned run-log fallback only suppresses RUN_ID=unknown, but failed-publish with a real run id still gets a synthetic larch-logs path. Scenario: When design-log publish fails after a non-empty SESSION_ID, render-final-summary passes RUN_LOGS_PATH=N/A for outcome failed-publish, then render-run-summary rebuilds larch-logs/design/<run-id>/ and advertises logs that did not publish
- **Proposed resolution**: Extend the proposed guard to also skip fallback for failed-publish, and add a real-run-id failed-publish test alongside the unknown-run-id case

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-pause-save.sh:54-72
- **Concern**: The plan validates the effective REPO after sourcing source-env.sh, but source-env.sh can overwrite a malformed argv --repo before validation. Scenario: A direct call with --repo /abs and a source-env.sh that exports REPO=owner/repo would pass the proposed post-source validation, reach gh/state work, and violate the accepted fail-closed direct --repo requirement
- **Proposed resolution**: Preserve the parsed argv repo before sourcing and validate it immediately, or restore argv precedence after sourcing; add the malformed --repo regression with source-env.sh also exporting a valid REPO so the bypass is covered

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-resume-state
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:463-466
- **Concern**: Step 0b clarify sub-step 3 adds fail-closed publish parsing and DESIGN_LOG_* recovery metadata, but sub-step 6 still hard-exports SUMMARY_OUTCOME=cancelled-clarify into the Final summary block. Scenario: render-final-summary.sh only appends recovery bullets for failed-publish (skills/design/scripts/render-final-summary.sh:330-333); cancelled-clarify never reads DESIGN_LOG_* — operators see a clarify-cancel summary with no PR/recovery-branch guidance after a failed clarify publish
- **Proposed resolution**: In sub-step 6, branch before the Final summary block: when SESSION_ID is non-empty and PUBLISH_OK != true after sub-step 3 normalization, export DESIGN_LOG_PR_NUMBER/URL/RECOVERY_BRANCH and set SUMMARY_OUTCOME=failed-publish; keep cancelled-clarify only when publish was skipped or succeeded

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-resume-state
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-postplan-emit.sh:157-168; skills/design/SKILL.md:880-884; skills/design/scripts/test-design-postplan-emit.sh:350-363
- **Concern**: 1. [risk-integration] The plan forwards --repo in prompt-side pause checks but misses the design-postplan-emit.sh internal pause writer.. Scenario: For a non-default repo run, .pause-requested during the Step 2b post-plan driver execs design-pause-save.sh without --repo, so pause publish, issue-body read, marker write, and LOG_RECOVERY_BRANCH metadata can target the gh default repo instead of the intended repo. The new pause-save validation will not protect this path because the intended repo is never passed.
- **Proposed resolution**: Add a minimum repo-forwarding path for design-postplan-emit.sh: parse optional --repo or safely read export REPO from source-env.sh, validate OWNER/REPO, and pass ${REPO:+--repo "$REPO"} to design-pause-save.sh. Update the Step 2b/Gate re-emit call sites and test-design-postplan-emit.sh pause case to assert --repo is forwarded.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-envelope-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-init-runparams.sh:165-177; scripts/write-design-current-env.sh:82,206
- **Concern**: Planned pause --repo forwarding is not persisted into the current design env. Scenario: Later Bash blocks only regain shell state by sourcing current-design-env, but design-init-runparams receives --repo and then calls write-design-current-env.sh without forwarding it. After the plan adds ${REPO:+--repo "$REPO"} to pause preludes, REPO is still unset in those later subshells, so non-default repo pauses can still fall back to hub/default repo.
- **Proposed resolution**: Append [[ -n "$REPO" ]] && _wdce_args+=(--repo "$REPO") in design-init-runparams.sh before invoking write-design-current-env.sh, and add a structural/test pin that source-env/current-design-env includes REPO for non-default repo runs.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-summary-ops
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-run-summary.sh:235-235
- **Concern**: Plan adds publish-skipped but not Outcome bullet emission in primary or fallback renderers. Scenario: Primary and compose_self_fallback only print - **Outcome** for bailed/stalled/cancelled/failed patterns; publish-skipped matches approved/approved-partition (no Outcome bullet). Operators scanning bullets can treat publish-skipped like success; test-render-final-summary.sh matrix else branch (563-569) will require - **Outcome**: publish-skipped and fail
- **Proposed resolution**: Add publish-skipped to the Outcome case in scripts/render-run-summary.sh and skills/design/scripts/render-final-summary.sh compose_self_fallback (395); keep the planned Publish skipped note as additive

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-summary-ops
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:295-298; scripts/render-run-summary.sh:221-224
- **Concern**: The plan relies on RUN_LOGS_PATH=N/A to suppress failed-publish run-log advertising, but its proposed render-run-summary guard only exempts RUN_ID=unknown. The shared renderer will still replace N/A with larch-logs/design/<run-id>/ for failed-publish runs with a real SESSION_ID.. Scenario: When design-log-publish fails after Step 5c or clarify publish, the primary summary can show failed-publish recovery notes and also a Run logs path that was not merged; the degraded fallback prints N/A, so primary and fallback disagree and operators see a synthetic success path.
- **Proposed resolution**: Extend the render-run-summary fallback guard to skip synthesis for failed-publish as well as RUN_ID=unknown, and add render-run-summary plus render-final-summary primary/fallback tests asserting failed-publish Run logs stays N/A while approved real-run-id still renders the path.
