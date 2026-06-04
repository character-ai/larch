### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1575-1581
- **Concern**: Auto-repair shared-handler rewrite exceeds minimum fold scope. Scenario: Extra prompt-side repair/escalation logic ships with a mechanical driver change
- **Proposed resolution**: Ship fold + exit 4 + --skip-validate + review_budget removal first; defer auto-repair and keep the existing 3-option handler with Step 5c Override → --skip-validate

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1420-1527
- **Concern**: Missing Step 5c post-repair resume contract after exit 4. Scenario: Auto-repair succeeds and re-publishes but never runs summary emit or step-5c completion items
- **Proposed resolution**: Specify that handler success re-enters the publish parse fence and items 5–7, or loops the design-publish invoke until rc is not 4

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1462-1527
- **Concern**: Exit-4 repair retry is not normalized back into the Step 5c publish result. Scenario: The first design-publish.sh call can return 4, the shared handler can repair and re-run design-publish.sh successfully, but the surrounding Step 5c variables and gates still reflect the original _publish_rc=4, so final-summary emission, step-5c sentinel writing, and cleanup decisions can be skipped or mis-gated
- **Proposed resolution**: Make the rc4 branch a retry loop around design-publish.sh: after auto-repair or --skip-validate accept, replace _publish_out and _publish_rc with the retry result, parse the latest .design-publish-result.env through the same file-first path, then continue only when the retry rc is 0, 1, or 3; cancel exits without items 5-7

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-publish.sh:257-352; scripts/test-design-structure.sh:1326-1331
- **Concern**: Plan text misstates the unchanged publish-tail order by placing the reentry marker before publish and rename. Scenario: An implementer following that parenthetical could move design_reentry_marker_write ahead of successful design-log publish and [DESIGNED] rename, breaking the existing marker-after-publish contract and the structure test
- **Proposed resolution**: Remove the parenthetical order or correct it to the current contract: plan-block-write, diagrams upsert, design-log-publish, final summary render, [DESIGNED] rename, then design_reentry_marker_write; keep the tail otherwise unchanged

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:191-195
- **Concern**: Folded validator call omits set +e capture pattern used by design-postplan-emit.sh. Scenario: Under set -euo pipefail a non-zero invoke-plan-validator/design-driver rc (parse/validator crash) aborts before parsing VALIDATE_* or writing the defects-found result env; infra failures become unclassified shell exits instead of exit 2 fail()
- **Proposed resolution**: Mirror design-postplan-emit.sh: set +e around invoke-plan-validator.sh capture, parse KVs, then branch defects-found (exit 4) vs infra (fail exit 2)

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1118,1575-1585
- **Concern**: The proposed shared validator handler omits the existing Step 3 plan-review-loop defects caller. Scenario: When plan-review-loop auto-revises plan.txt and returns LOOP_STATUS=plan-validator-defects, Step 3 still routes into the shared handler, but the plan only defines auto-repair sites for Step 2b, Gate B, discussion-round2, and Step 5c. The handler may lack the target file, log source, and continuation semantics for this path.
- **Proposed resolution**: Add a minimal Step 3 site entry: target plan.txt, read the existing validate-plan-commands.log default, revalidate via design-postplan-emit.sh, then preserve the current Step 3 Gate-B-bypass continuation to Step 3b.

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:193-209
- **Concern**: The planned redaction pipeline lacks explicit nonzero handling. Scenario: With set -euo pipefail, a redact-secrets.sh sed/awk failure can abort design-publish.sh with the raw child exit code before the planned exit-2 contract or result handling, making Step 5c see an unexpected driver failure.
- **Proposed resolution**: Wrap the redaction command in an if ! pipeline; on failure call fail "redact-secrets.sh failed", then keep the planned non-empty redacted-file check.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:4,10-14
- **Concern**: Validator invoke not planned under set +e. Scenario: design-postplan-emit.sh wraps invoke-plan-validator in set +e (design-postplan-emit.sh:265-268); design-publish.sh keeps set -euo pipefail. Any non-zero invoke/design-driver rc before VALIDATE_STATUS is parsed aborts the driver as exit 2 instead of the planned defects-found (exit 4) or infra-fail path
- **Proposed resolution**: Wrap the folded invoke-plan-validator.sh call in set +e; parse stdout; branch on VALIDATE_STATUS=defects-found vs empty/not-run vs rc!=0 exactly like design-postplan-emit.sh

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1577-1581
- **Concern**: The proposed auto-repair-then-escalate handler is scope creep for a SIMPLE lane. Scenario: The existing shared Fix-and-retry / Override / Cancel handler already blocks unsafe publish and gives an operator override; adding root-cause diagnosis, prompt-side artifact edits, retry caps, and new option labels expands the change surface and can stale the current structure pins for those labels
- **Proposed resolution**: Keep the existing shared handler shape; only add the Step 5c exit-4 routing and make the existing Override path call design-publish.sh --skip-validate for composed-plan publish

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1420-1537
- **Concern**: The Step 5c retry contract is underspecified if the handler re-runs design-publish.sh. Scenario: After an exit-4 defect, the proposed handler may re-run design-publish.sh and publish successfully, but the outer Step 5c block can still hold the original _publish_rc=4 / _publish_out and skip summary emission, step-5c sentinel, and footer handling
- **Proposed resolution**: Do not publish inside the shared handler; have it repair composed-plan.md and return to one outer design-publish.sh invocation, or explicitly require the retry to replace _publish_rc, _publish_out, and parsed result state before falling through to Step 5c items 5-7

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-publish.sh:191-194
- **Concern**: The proposed redaction pipeline is not mapped onto the driver exit-code contract. Scenario: If redact-secrets.sh, sed/awk, or the output redirection fails, set -e/pipefail can exit with a raw non-2 status such as 1, which collides with the plan-block-write failure path and may leave no clear result contract
- **Proposed resolution**: Wrap the redaction pipeline in an explicit if ! ...; then fail 'redact-secrets.sh failed'; fi block, then separately check the redacted file is non-empty before publishing

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1477-1521
- **Concern**: Driver exit-code contract still aborts outside {0,1,3} only. Scenario: _publish_rc=4 treated as fatal publish error despite defects-found result env
- **Proposed resolution**: Widen contract to {0,1,3,4}; document exit 4 handler routing; insert handler prose before items 5-7

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1489-1514
- **Concern**: Step 5c parse fence omits VALIDATE_* keys. Scenario: _exit 4 branch cannot load VALIDATE_LOG_FILE/counts for shared handler
- **Proposed resolution**: Add VALIDATE_STATUS and four sibling keys to result-env parse case arms

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:proposed-validate-fold
- **Concern**: Missing set +e around invoke-plan-validator. Scenario: Infra validator failure aborts under set -e before result env is written
- **Proposed resolution**: Mirror design-postplan-emit.sh set +e capture parse then branch exit 4 vs exit 2

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1575-1581
- **Concern**: Auto-repair attempt cap is not persisted. Scenario: Pause resume or multi-turn loops can exceed two silent repairs
- **Proposed resolution**: Add DESIGN_TMPDIR attempt counter file and read increment in handler

### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:Approach
- **Concern**: Bundled LLM auto-repair with mechanical fold. Scenario: Minimum-change SIMPLE PR carries high regression and halt risk
- **Proposed resolution**: Ship fold exit 4 and review_budget removal first; defer handler rewrite

### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:335
- **Concern**: Structural pin still encodes quick-skip owner. Scenario: make lint passes while SKILL prose drifts on unconditional validation
- **Proposed resolution**: Repin assertion to unconditional validation contract not quick-skip owner

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1575-1581
- **Concern**: The proposed shared validator handler adds silent auto-repair of plan artifacts, which is scope creep for the SIMPLE minimum-change lane. Scenario: After Gate B or Gate C approval, the handler may edit plan.txt or composed-plan.md and continue without a prompt, changing the reviewed/published design based on heuristic diagnosis; the two-attempt cap limits loops but not unintended content drift
- **Proposed resolution**: Keep the existing prompt-first handler shape, or limit the change to root-cause display plus user-approved fix/accept/cancel; do not auto-edit plan artifacts in this PR

### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-publish.sh:332-352; scripts/test-design-structure.sh:1326-1331
- **Concern**: Plan describes the publish tail as plan-block-write -> marker -> diagrams -> publish -> summary -> rename even though the code and structure test require the reentry marker only after successful log publish and designed rename. Scenario: If implementer follows the plan order while folding validation, a failed publish or rename can still leave a completed reentry marker and make later reentry think the design finished
- **Proposed resolution**: Preserve the existing code order and update the plan/docs wording to say plan-block-write -> upsert -> log publish -> post-publish summary -> rename -> design_reentry_marker_write

### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-publish.sh:191-209
- **Concern**: Plan moves redact-secrets.sh into design-publish.sh but only specifies an empty-output check, not handling a non-zero redactor or redirection failure. Scenario: With set -euo pipefail, a redaction failure can exit with an arbitrary helper rc and no result env, violating the driver exit-code contract and giving the caller misleading plan-write diagnostics
- **Proposed resolution**: Wrap redaction with if ! redact-secrets.sh ...; then fail 'redact-secrets.sh failed'; fi before the non-empty check, and add a test-design-publish case asserting rc 2 and no publish on redactor failure

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1575-1581
- **Concern**: Proposed shared-handler rewrite silently auto-repairs and republishes after validator defects. Scenario: The current handler is user-mediated; the plan would let Step 5c change composed-plan.md after Gate C approval and re-run design-publish.sh, so a command-line fix can be published without operator acceptance
- **Proposed resolution**: For SIMPLE, keep the folded driver and exit-4 hand-back but retain a prompt-mediated Fix/Override/Cancel path or require confirmation before publishing any Step 5c auto-repair

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-handoff-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1470-1518
- **Concern**: Step 5c unexpected-rc abort runs before parse and treats rc 4 as fatal. Scenario: exit 4 from folded validation aborts /design instead of shared handler
- **Proposed resolution**: Widen guard to include 4; add explicit rc==4 branch that parses VALIDATE_* and runs shared handler before items 5-7

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-handoff-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:624-626
- **Concern**: (14b12) preserve-tmpdir needle only in deleted Step 5c validator prose. Scenario: CI structural test fails after SKILL fold
- **Proposed resolution**: Add literal preserve/skip-cleanup phrase to exit-4 or shared-handler Cancel prose or update pin

### FINDING_24:
- **Reviewer(s)**: Cursor-dyn-handoff-control
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:1348,1374
- **Concern**: Plan omits updating (15b) greps hardcoding rc set {0,1,3}. Scenario: Widened SKILL contract fails existing structure pins
- **Proposed resolution**: Extend plan to retarget 1348/1374 and driver contract text to {0,1,3,4}

### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-handoff-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1493-1500
- **Concern**: Step 5c parse fence lacks VALIDATE_* case arms. Scenario: Handler on exit 4 cannot read VALIDATE_LOG_FILE from result env
- **Proposed resolution**: Add VALIDATE_* keys to file-first/stdout parse before shared handler

### FINDING_26:
- **Reviewer(s)**: Cursor-dyn-handoff-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:1-4
- **Concern**: Folded validator needs set +e under set -euo. Scenario: Infra validator failure skips exit 2/4 handling
- **Proposed resolution**: Wrap invoke-plan-validator in set +e; branch on VALIDATE_STATUS like design-postplan-emit

### FINDING_27:
- **Reviewer(s)**: Cursor-dyn-handoff-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1575-1581
- **Concern**: Shared handler still Override-centric; --skip-validate accept only in Approach. Scenario: Operator accept at Step 5c may not re-publish with skip flag
- **Proposed resolution**: Rewrite shared handler in SKILL.md with auto-repair + Accept re-invoke design-publish.sh --skip-validate

### FINDING_28:
- **Reviewer(s)**: Codex-dyn-handoff-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1461-1527
- **Concern**: Exit-4 repair and accept re-runs are not required to refresh Step 5c publish state. Scenario: The plan routes _publish_rc=4 to the shared handler, but after auto-repair or Accept re-invokes design-publish.sh, Step 5c items 5-7 still depend on _publish_rc, PLAN_WRITE_OK, FINAL_SUMMARY_PATH, and WARN state from the publish capture/parse block. If those variables are not replaced with the second run's result, the flow can skip the final summary or preserve the tmpdir despite a successful publish.
- **Proposed resolution**: Specify that the rc4 branch tail-calls or repeats the same design-publish capture plus file-first/stdout parse path after repair or --skip-validate accept, then continues items 5-7 only with the re-run _publish_rc and parsed result env. Cancel must exit that path before items 5-7.

### FINDING_29:
- **Reviewer(s)**: Codex-dyn-harness-oracle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-postplan-emit.sh:147-151,294-303; skills/design/scripts/design-postplan-emit.sh:97,262-280
- **Concern**: Finding 1: Planned postplan tests delete quick-skip coverage but do not add a legacy review_budget=quick assertion. Scenario: An implementation can leave the current REVIEW_BUDGET reader and quick skip branch in place; new normal fixtures without review_budget still pass, but a legacy run-params.json with review_budget=quick still skips validation, contradicting the plan's legacy ignored/no reader contract
- **Proposed resolution**: Add one legacy fixture with review_budget=quick that expects the validator stub to run and VALIDATE_STATUS=ok, or add a structure assertion that REVIEW_BUDGET, skipped-quick, and --force-validate are absent from design-postplan-emit.sh

### FINDING_30:
- **Reviewer(s)**: Codex-dyn-harness-oracle
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-write-run-params.sh:42-58,191-245; scripts/write-run-params.sh:197-218
- **Concern**: Finding 2: Planned run-params harness removes review_budget checks without replacing them with absence and unknown-flag checks. Scenario: The writer could keep emitting review_budget:null or keep accepting --review-budget full while the planned tests still pass, leaving schema drift in schema_version 3
- **Proposed resolution**: Add jq assertions that has("review_budget") is false for emitted JSON, and add an argv rejection case for --review-budget full as an unknown flag

### FINDING_31:
- **Reviewer(s)**: Codex-dyn-harness-oracle
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:348-350,559-562; skills/design/references/flags.md:17-25,70; skills/design/references/approval-gates.md:157; skills/design/references/discussion-rounds.md:126
- **Concern**: Finding 3: Planned structure changes remove stale quick/force pins but do not assert the stale docs are gone. Scenario: Docs can still tell the orchestrator to pass --force-validate or rely on skipped-quick after the script drops that flag, producing runtime exit 2 or unvalidated paths despite the tests passing
- **Proposed resolution**: Add narrow absent checks in test-design-structure.sh for --force-validate, skipped-quick, and review_budget quick/full in the affected design docs and SKILL helper prose where the plan says those contracts are removed
