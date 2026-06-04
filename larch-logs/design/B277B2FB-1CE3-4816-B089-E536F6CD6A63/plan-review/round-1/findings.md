### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:93-95
- **Concern**: Plan does not require LARCH_QUIET_DISABLE=1 when --with-plan-size invokes check-plan-size.sh. Scenario: Under larch_quiet_init, child emit_kv lines go to FD 3/quiet log, not command-substitution stdout; driver cannot parse HARD_TRIGGER_FIRED and related KVs, breaking rc 12/13 mapping and display emission
- **Proposed resolution**: Invoke check-plan-size with export LARCH_QUIET_DISABLE=1 (same capture contract as SKILL.md Step 2b.5:985-987) and parse stdout KVs into the result env before emit display lines

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:973-1015
- **Concern**: Merged rc 0 → Step 3 omits .completed/step-2b.5 and leaves Run Step 2b.5 now. Scenario: Initial path skips the Step 2b.5 procedure but still has the unconditional sentinel prose and explicit Run Step 2b.5 now; pause-resume and step-registry tests expect step-2b.5 after a successful size check
- **Proposed resolution**: In thin-fence rc 0 arms (initial, Gate B, Gate A re-entry, discussion-round2), write step-2b.5 before continuing; delete Run Step 2b.5 now on merged paths; keep the standalone procedure for Override and Step 3 short-circuits

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:992-993
- **Concern**: --with-plan-size non-fatal rc 2/3 only appends WARN; standalone Step 2b.5 also logs validation.log and append-tool-failure.sh. Scenario: Contradicts preserve all behavior; merged emit sites lose execution-issues.md and check-plan-size.validation.log records on threshold-helper failure
- **Proposed resolution**: Mirror Step 2b.5 rc 2/3 handling in the driver: write capture to check-plan-size.validation.log, call append-tool-failure.sh, then WARN and exit 0; document in design-postplan-emit.md

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.sh:184-188
- **Concern**: Fourth merged caller (Step 1e Gate A optional-trailer guard ~636) not pinned for --with-plan-size. Scenario: Plan updates that re-emit but structure tests only pin Step 2b, Gate B, and discussion-round2; regression can leave fat file-first parse on Gate A re-entry
- **Proposed resolution**: Add assert_thin_fence or contains pin for the Gate A re-entry block with --with-plan-size and rc arms, alongside the three existing site pins

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:942-960
- **Concern**: --with-plan-size thin fence removes status parsing while design-postplan-emit.sh still multiplexes operation failures onto exit 1. Scenario: With KVs suppressed from FD 3, missing diff_lines, snapshot failure, emit failure, and validator infra failure all look like rc 1, so the proposed case fence cannot preserve the existing targeted abort messages
- **Proposed resolution**: Keep a minimal rc1-only status read, add distinct failure exit codes, or make the driver emit the existing human-readable failure line before exit 1 in --with-plan-size mode

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:992-993
- **Concern**: Merged plan-size failure path drops the current execution-issues.md warning/log contract. Scenario: check-plan-size.sh rc 2 or 3 at a merged site would only surface a WARN/display line, losing the check-plan-size.validation.log and execution-issues.md Warnings entry that Step 2b.5 writes today
- **Proposed resolution**: In design-postplan-emit.sh --with-plan-size, reuse the existing Step 2b.5 append-tool-failure logging path for check-plan-size rc 2 and rc 3 before returning cleanly

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1577-1580
- **Concern**: rc10 Fix-and-retry can bypass the merged plan-size check. Scenario: With --with-plan-size the driver exits 10 before running check-plan-size.sh. If the existing shared validator body only reruns ACTION=EMIT_PLAN plus validation, a fixed-but-large or partition_requested plan can proceed without the Step 2b.5 gate after defects are resolved.
- **Proposed resolution**: Update the rc10 contract so Fix-and-retry reruns the same site's design-postplan-emit.sh --with-plan-size driver and dispatches its rc again, or explicitly runs retained Step 2b.5 after validation succeeds.

### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:942-960; skills/design/scripts/design-postplan-emit.sh:144-173
- **Concern**: The thin rc1 fence loses the status needed for existing failure-specific abort messages. Scenario: The plan removes result-env/stdout parsing and suppresses KV output in --with-plan-size, but still says rc1 aborts with existing messages. On missing diff_lines, snapshot failure, or validator infrastructure failure, the site case only sees rc=1 unless the driver emits the human message itself.
- **Proposed resolution**: Either have --with-plan-size emit the existing rc1 human failure messages before exit 1, or keep a minimal rc1-only result-env read for POSTPLAN_EMIT_STATUS; add with-plan-size tests for the rc1 subcases.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:973-1015; scripts/design-pause-save.sh:82-95
- **Concern**: The merged Step 2b rc0 path skips the existing step-2b.5 completion sentinel. Scenario: After a clean merged driver result, /design proceeds to Step 3 without running the standalone Step 2b.5 body that currently writes .completed/step-2b.5; if the run pauses before Step 3 completes, design-pause-save picks the first missing registry step and resumes at Step 2b.5 instead of Step 3, causing duplicate plan-size handling or prompts
- **Proposed resolution**: Write both .completed/step-2b and .completed/step-2b.5 on the initial Step 2b rc0 clean branch before entering Step 3, and pin that sentinel preservation in scripts/test-design-structure.sh

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:972-1015; scripts/design-pause-save.sh:81-95
- **Concern**: Merged Step 2b clean path does not preserve the Step 2b and Step 2b.5 completion sentinels. Scenario: After rc 0 jumps straight to Step 3, a pause before Step 3 completion makes design-pause-save scan the registry and resume at 2b or 2b.5, rerunning the plan-size gate or split prompt
- **Proposed resolution**: Keep the minimum sentinel contract: on initial rc 0 write .completed/step-2b and .completed/step-2b.5 before Step 3; on Override-to-standalone Step 2b.5 write step-2b before the retained procedure and step-2b.5 before Step 3; pin this in test-design-structure.sh

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:992-993
- **Concern**: The merged nonfatal check-plan-size path preserves the chat WARN but not the existing execution-issues warning log. Scenario: When check-plan-size.sh exits 2 or 3 under --with-plan-size, the standalone Step 2b.5 contract currently records the failure in execution-issues.md; the proposed driver path would only emit WARN, so final logs lose a preserved diagnostic
- **Proposed resolution**: Add the same check-plan-size.validation.log plus append-tool-failure Warnings write in the driver rc2/rc3 path, and extend the nonfatal harness case to assert it

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-exit-code-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1577-1581
- **Concern**: The plan does not explicitly update the shared validator-defect body even though --with-plan-size makes rc10 skip plan-size. Scenario: After rc10 defects, the current Fix-and-retry body re-runs raw EMIT_PLAN plus VALIDATE_PLAN_COMMANDS and then continues; with Step 2b.5 removed from the clean merged sites, a fixed plan can skip rc12 hard and rc13 partition handling
- **Proposed resolution**: Revise the shared body or each rc10 arm so Fix-and-retry re-enters the same site-specific design-postplan-emit.sh --with-plan-size fence and Override runs the retained standalone Step 2b.5 before proceeding

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-exit-code-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:994; skills/design/SKILL.md:1117; skills/design/scripts/plan-review-loop.md:53; skills/design/references/approval-gates.md:163
- **Concern**: The retained standalone Step 2b.5 hard handler is not made site-aware even though retained callers need the Gate B style Override option. Scenario: plan-review-loop hard triggers and Gate B defect-Override reroutes can land in the standalone Step 2b.5 procedure, whose current hard prompt is Split/Cancel only, conflicting with the Split/Override/Cancel contract documented for Gate B and plan-review-loop
- **Proposed resolution**: Keep the minimum change by documenting/coding two named hard-prompt bodies: initial/discussion use Split/Cancel, while Gate B and Step 3 plan-size-trigger retained callers use Split/Override/Cancel before continuing their surrounding flow

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-shell-io-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-postplan-emit.sh:226-269; skills/design/scripts/design-postplan-emit.sh:99-116; scripts/lib-quiet.sh:158-178
- **Concern**: The proposed with-plan-size harness does not cover classification-stderr WARN propagation through the new display-only channel. Scenario: Existing #3441 tests cover the non-flag WARN= stdout-KV path, but --with-plan-size suppresses emit_kv and must replay WARN bodies with emit; a regression could drop the warning or leak WARN= while the listed clean/no-KV and plan-size-failure WARN cases still pass
- **Proposed resolution**: Add one --with-plan-size classification-warning fixture, reusing the missing/invalid run-params setup, asserting the warning body appears in stdout, stdout has no full-line KEY=VALUE or WARN= leakage, and .design-postplan-emit-result.env still contains WARN= for diagnostics

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-prompt-flow-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:994,1117,1577-1581; skills/design/references/approval-gates.md:157-163; skills/design/scripts/plan-review-loop.md:51-53
- **Concern**: The retained Step 2b.5 / validator Override route is not specified as site-specific, leaving the existing Split/Override/Cancel contracts inconsistent with the two-option standalone hard prompt.. Scenario: If Gate B re-emit returns rc 10, Override then re-runs standalone Step 2b.5; a hard-size plan gets only Split/Cancel even though Gate B and plan-review-loop promise Split/Override/Cancel.
- **Proposed resolution**: Specify that Override-after-defects and Step 3 plan-size-trigger invoke the correct site hard prompt: Gate B / plan-review-loop get Split/Override/Cancel; initial Step 2b and discussion-round2 keep Split/Cancel.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-prompt-flow-sync
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/check-plan-size.md:71-73; skills/design/scripts/plan-review-loop.sh:22,601
- **Concern**: The check-plan-size script docs update adds the new driver caller but still omits the retained direct plan-review-loop caller.. Scenario: Future threshold/contract edits following check-plan-size.md may update design-postplan-emit and Step 2b.5 but miss plan-review-loop.sh, which directly calls check-plan-size.sh during multi-round revision.
- **Proposed resolution**: Add plan-review-loop.sh to the callers / edit-in-sync list alongside design-postplan-emit.sh --with-plan-size.

### OOS_1:
- **Description**: Step 3.5 prose still says Gate B requires Step 2b.5 immediately after each settled design-postplan-emit.sh re-emit. Scenario: After merge, operators and agents may follow stale two-call sequencing at Gate B despite approval-gates rewrite
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1154
- **Phase**: design
