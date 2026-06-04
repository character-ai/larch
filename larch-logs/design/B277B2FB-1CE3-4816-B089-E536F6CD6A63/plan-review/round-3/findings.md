### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:39-45
- **Concern**: The plan tells the new merged driver to read boolean partition_requested with json_scalar_or_sed, but that helper's sed fallback only parses quoted string JSON values. Scenario: On a host without jq, run-params.json stores "partition_requested": true as a boolean, the merged --with-plan-size path defaults it to false, and rc13 Split routing is skipped
- **Proposed resolution**: Update the helper or this call to parse unquoted true/false booleans in the fallback, and add the partition rc13 test with jq hidden from PATH

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:936-964
- **Concern**: Thin-fence rewrite does not explicitly retire the fat-fence guards that treat only rc 0/1 as success and abort on any other rc. Scenario: After `--with-plan-size`, driver rc 10/11/12/13 hits the mandatory-key check (rc not 0 or 1) or the final `_postplan_rc -ne 0` abort before any `case` arm runs — defects/hard/partition/pause never reach their handlers
- **Proposed resolution**: In the collapsed Step 2b / Gate B / discussion / Gate A fences, mirror Step 3.6: `echo` display, `case "$_postplan_rc"`, handle 10/11/12/13/2/1 explicitly, and delete the catch-all abort plus the rc 0-or-1-only mandatory-key gate (or extend it to action codes)

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:39-46; scripts/write-run-params.sh:204-215
- **Concern**: Proposed --with-plan-size reads partition_requested with json_scalar_or_sed, but the sed fallback only parses quoted strings while run-params writes partition_requested as an unquoted JSON boolean. Scenario: If jq is absent, a user running /design --partition gets partition_requested defaulted to false, so the merged driver returns clean rc0 instead of rc13 and silently skips the requested Split path
- **Proposed resolution**: Before using this helper for partition_requested, extend its fallback to parse unquoted true/false booleans, or fail closed when jq is unavailable for this boolean; add a jq-absent partition_requested=true test in test-design-postplan-emit.sh

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:62-63
- **Concern**: Step 1e is pinned to the discussion-round2 template including implied --force-validate. Scenario: Gate A optional-trailer re-entry currently calls design-postplan-emit without --force-validate (skills/design/SKILL.md:636); copying discussion-round2 would force validation on quick review_budget runs and change Gate A behavior
- **Proposed resolution**: Specify Step 1e uses --with-plan-size only (match Gate B); reserve --force-validate for discussion-round2; pin argv separately in test-design-structure.sh

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:28-31
- **Concern**: Thin fence drops stdout KV merge but omits rc 10/Override validator state handoff. Scenario: --with-plan-size puts VALIDATE_* only in .design-postplan-emit-result.env while SKILL.md Step 2b fat parse is removed; rc 10 Fix-and-retry/Override/Cancel needs VALIDATE_DEFECT_COUNT and VALIDATE_LOG_FILE
- **Proposed resolution**: After echo "$out", read allowlisted keys from .design-postplan-emit-result.env in rc 10 and Override arms only (never source); document in design-postplan-emit.md and thin-fence SKILL.md prose

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:515-517
- **Concern**: Plan retires fat inline parse but not all conflicting structure pins. Scenario: contains checks for .design-postplan-emit-result.env and <<<"${_postplan_out:-}" will fail once Step 2b collapses to driver+echo+case; FINDING_21 check-plan-size.sh-after-postplan in Step 2b block (689-694) will fail when check-plan-size moves into the driver
- **Proposed resolution**: List explicit retirements: lines 515-517, 689-694, and any pin requiring stdout KV merge or literal check-plan-size.sh in the Step 2b region; replace with --with-plan-size and assert_thin_fence pins per plan lines 155-167

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/append-execution-issue.sh:171-172
- **Concern**: Nonfatal plan-size logging can leak helper KVs despite the --with-plan-size no-KV contract. Scenario: The rc2/3 path appends execution issues via append-tool-failure.sh, whose child emits APPENDED= and LOG= on success; under LARCH_QUIET_DISABLE=1 or harness conditions those lines can appear in the driver capture and violate the proposed display-only output discipline
- **Proposed resolution**: Capture or redirect append-tool-failure.sh output in the --with-plan-size rc2/3 block, and add the nonfatal rc2/3 test assertion that stdout has no APPENDED= or LOG= lines

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:878-970 (proposed thin fence) / plan Approach §Output discipline
- **Concern**: `--with-plan-size` puts validator/plan-size KVs only in `.design-postplan-emit-result.env` while the plan collapses fences to `echo "$out"` + `case rc`. Scenario: Merged rc 10/Override arms of **### Plan command validator failure (shared)** need `VALIDATE_DEFECT_COUNT`, `VALIDATE_LOG_FILE`, etc.; with no FD3 KV mirror those fields will not be in `_postplan_out`, so Fix-and-retry/Override can fire with empty defect context
- **Proposed resolution**: In `design-postplan-emit.md` orchestrator handoff and each merged thin-fence site, specify an allowlisted read of `.design-postplan-emit-result.env` on rc 10 (and Override continuation), mirroring Step 3.6’s rc-specific state handling—not the removed fat stdout merge loop

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:39-47
- **Concern**: Plan reuses json_scalar_or_sed to read partition_requested, but its sed fallback only parses quoted strings and not JSON booleans. Scenario: When jq is unavailable or the fallback path is exercised, partition_requested: true is read as false, so the new --with-plan-size driver skips the requested rc13 Split path
- **Proposed resolution**: Add a tiny boolean-capable reader or extend the sed fallback to parse bare true/false before defaulting false, and cover this in the new --with-plan-size partition test

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:515-517
- **Concern**: Plan retires fat inline parse but leaves structure-test pins for fat-fence artifacts. Scenario: After Step 2b collapses to driver capture plus echo plus case rc, contains checks for .design-postplan-emit-result.env and <<<"${_postplan_out:-}" still fail CI or block the thin-fence migration
- **Proposed resolution**: Add an explicit test-design-structure.sh task: drop or repoint lines 515-516 for merged sites; keep only pins still valid on thin fences (for example rc=2 abort prose at 517 if retained in the case arm)

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:39-46
- **Concern**: Plan says to read partition_requested with json_scalar_or_sed, but that helper's sed fallback only parses quoted JSON strings while run-params writes partition_requested as a boolean.. Scenario: If jq is unavailable or fails, --partition is silently read as false, so --with-plan-size returns rc0 instead of required rc13 for small plans.
- **Proposed resolution**: Extend the helper or add a boolean-specific reader that parses unquoted true/false, and add a --with-plan-size test that forces the no-jq fallback for partition_requested=true.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-contract-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1575-1580
- **Concern**: Shared Plan command validator failure Fix-and-retry still prescribes raw ACTION=EMIT_PLAN plus ACTION=VALIDATE_PLAN_COMMANDS. Scenario: Merged rc10 arms require same-site re-entry of design-postplan-emit.sh --with-plan-size; orchestrators following the shared section re-run legacy emit/validate and skip plan-size mapping/sentinel writes
- **Proposed resolution**: Update Fix-and-retry/Override bullets (and edit-in-sync list) to name --with-plan-size re-entry per site; retain raw emit/validate only for Step 5c composed-plan path

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-contract-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1012-1015; skills/design/references/approval-gates.md:157-163
- **Concern**: Merged Gate B rc12 Override can continue without writing the Step 2b.5 sentinel. Scenario: The plan moves Gate B hard-size handling into the merged rc12 arm, but only names rc0 clean and Split Refine returns as sentinel writers. If the operator picks Override, the legacy standalone Step 2b.5 success boundary no longer runs, so pause/resume can see Step 2b.5 as incomplete before Step 3.6
- **Proposed resolution**: Add the same .completed/step-2b.5 write/update to the Gate B rc12 Override arm before Step 3.6, and pin that arm in scripts/test-design-structure.sh

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-contract-matrix
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/flags.md:21-44; skills/design/references/approval-gates.md:163; skills/design/scripts/plan-review-loop.md:53
- **Concern**: flags.md would keep a global Split/Cancel hard-size contract that conflicts with Gate B and plan-review-loop Override. Scenario: The plan updates approval/check docs for site-aware prompts, but its flags.md update list omits the existing public flag text that says hard plans show Split/Cancel and have no override. That contradicts Gate B and plan-review-loop retained paths, which must offer Split/Override/Cancel
- **Proposed resolution**: Update flags.md’s plan-size prose to say hard prompts are site-aware: initial and discussion use Split/Cancel; Gate B and plan-review-loop use Split/Override/Cancel

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-contract-matrix
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:584-620; skills/design/scripts/check-plan-size.md:63-70
- **Concern**: Retained plan-review-loop caller is not covered by the proposed nonfatal rc2/rc3 plan-size contract. Scenario: plan-review-loop.sh calls check-plan-size.sh directly under set -e. If check-plan-size returns rc2 or rc3, the loop can exit before writing the documented LOOP_STATUS handoff, while the plan says rc2/rc3 are nonfatal and preserved for retained standalone paths
- **Proposed resolution**: Add a minimal set +e capture around the plan-review-loop check-plan-size call and handle rc2/rc3 as warning-and-continue, matching the standalone Step 2b.5 diagnostic contract without changing check-plan-size.sh

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-sentinel-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/decompose-panel.md:80-81
- **Concern**: Merged-path Refine-return sentinel not wired in normative Split-path doc. Scenario: Plan pins Refine `.completed/step-2b.5` writes in SKILL.md / approval-gates / discussion-rounds only; Split-path entry requires reading decompose-panel.md first, so implementers can omit the write on merged rc12/rc13 Refine
- **Proposed resolution**: Add `skills/design/references/decompose-panel.md` to Files to modify/create; in §4 Stage 0 option 3 (and §9 terminal outcomes), require `mkdir -p "$DESIGN_TMPDIR/.completed" && : > "$DESIGN_TMPDIR/.completed/step-2b.5"` before return when the caller used `--with-plan-size` (merged fence), matching SKILL.md Refine arms

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-sentinel-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:157-163; skills/design/SKILL.md:1012-1013
- **Concern**: Gate B rc12 Override is not assigned a step-2b.5 sentinel write. Scenario: The plan covers Gate B rc0 clean writes and rc12/rc13 Split Refine writes, but Gate B hard Override continues from the merged rc12 prompt without entering the retained standalone Step 2b.5 success boundary that currently writes .completed/step-2b.5. Pause/resume can later miss that Step 2b.5 was accepted for this Gate B revision.
- **Proposed resolution**: Add a narrow Gate B rc12 Override arm requirement: before continuing to Step 3.6, run mkdir -p "$DESIGN_TMPDIR/.completed" and : > "$DESIGN_TMPDIR/.completed/step-2b.5"; add a matching scripts/test-design-structure.sh pin for Gate B hard Override.

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-stream-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:991-991
- **Concern**: Plan output discipline lists soft-advisory FD3 display but not the co-occurring hard-trigger variant when SOFT_ADVISORY=true and HARD_TRIGGER_FIRED=true. Scenario: Standalone Step 2b.5 and plan-review-loop.sh emit a second breadcrumb ("plan-body gate still requires Split/Cancel" or Split/Override/Cancel) before the hard branch; merged --with-plan-size rc12 can omit it and operators lose the downgrade context
- **Proposed resolution**: Pin both soft-advisory emit strings in design-postplan-emit.md and the driver spec: advisory-only on clean rc0; advisory plus hard-section preamble before exit 12 when both flags are true

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-stream-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:22-27,77-78; skills/design/scripts/check-plan-size.sh:38-49; scripts/lib-quiet.sh:43-44,147-149
- **Concern**: The plan requires stdout-only plan-size capture while also preserving rc3 diagnostics, but check-plan-size rc3 writes diagnostics to stderr only. Scenario: With LARCH_QUIET_DISABLE=1, larch_err stays on stderr, so stdout-only capture makes check-plan-size.validation.log and execution-issues.md omit the rc3 usage or tmpdir-validation diagnostic
- **Proposed resolution**: Capture stderr separately for nonzero plan-size runs, keep stdout-only KV parsing, and combine stdout plus stderr only for the validation log and append-tool-failure entry.

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-harness-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:157-159
- **Concern**: Shared post-apply step 8 still keys defects and clean continuation on driver exit 0 plus a follow-on standalone Step 2b.5 call. Scenario: After --with-plan-size, defects return rc 10 and clean paths return rc 0 with plan-size already folded; following step 8 literally can re-run Step 2b.5 after defects or never branch on rc 10, breaking defects-priority
- **Proposed resolution**: Rewrite steps 7-9 for --with-plan-size: rc 10 to shared validator failure (same-site re-entry), rc 0 to sentinel write then Step 3.6 without standalone 2b.5, rc 12/13 to Split arms; keep standalone Step 2b.5 only for Override and LOOP_STATUS=plan-size-trigger

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-harness-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:128-143,171-172
- **Concern**: The planned harness tests hard and partition routes separately but does not test the hard+partition co-occurrence precedence. Scenario: An implementation that checks partition before hard would still pass the listed rc12-only and rc13-only cases while violating the stated hard-wins contract
- **Proposed resolution**: Add one minimal --with-plan-size test with partition_requested=true and a hard-sized plan, asserting rc 12 and not rc 13

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-harness-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:22-27; skills/design/scripts/check-plan-size.sh:39-49; skills/design/scripts/check-plan-size.md:63-70
- **Concern**: The plan promises rc 3 diagnostics logging while also requiring stdout-only capture, but check-plan-size rc 3 diagnostics are stderr-only. Scenario: A check-plan-size argv/config error exits 3; stdout capture is empty, so check-plan-size.validation.log and execution-issues.md lose the actual diagnostic even though the plan says rc 2/3 diagnostics are preserved
- **Proposed resolution**: Capture stderr to a sidecar for nonzero plan-size exits without parsing it as KVs, append that file for rc 3, and assert the rc 3 stderr text appears in the validation log

### FINDING_23:
- **Reviewer(s)**: Codex-dyn-harness-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:122-126,154-167; skills/design/scripts/plan-review-loop.md:51-53; skills/design/SKILL.md:994-1006
- **Concern**: The structural-test plan says to keep standalone Step 2b.5 anchors, but does not pin the retained caller prompt split between Split/Cancel and Split/Override/Cancel. Scenario: A broad Step 2b.5 rewrite could remove Override from the plan-review-loop or Gate B retained hard-size path while still proving the standalone procedure exists
- **Proposed resolution**: Add narrow structure assertions that retained plan-review-loop and Gate B hard-size prompts include Split / Override / Cancel, while initial/discussion retained prompts stay Split / Cancel
