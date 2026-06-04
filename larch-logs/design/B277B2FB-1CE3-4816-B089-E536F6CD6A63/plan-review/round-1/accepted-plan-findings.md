### FINDING_2: Merged clean paths must preserve Step 2b / Step 2b.5 completion sentinels
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: Clean merged `rc 0` paths can proceed to Step 3 without writing the existing `.completed/step-2b` / `.completed/step-2b.5` sentinels, causing pause/resume to restart at the wrong step and potentially rerun plan-size handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In thin-fence rc 0 arms (initial, Gate B, Gate A re-entry, discussion-round2), write step-2b.5 before continuing; delete Run Step 2b.5 now on merged paths; keep the standalone procedure for Override and Step 3 short-circuits
  - From Codex-Innovation: Write both .completed/step-2b and .completed/step-2b.5 on the initial Step 2b rc0 clean branch before entering Step 3, and pin that sentinel preservation in scripts/test-design-structure.sh
  - From Codex-Pragmatic: Keep the minimum sentinel contract: on initial rc 0 write .completed/step-2b and .completed/step-2b.5 before Step 3; on Override-to-standalone Step 2b.5 write step-2b before the retained procedure and step-2b.5 before Step 3; pin this in test-design-structure.sh


### FINDING_3: Nonfatal plan-size failures must preserve validation log and execution-issues contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The merged `check-plan-size.sh` `rc 2/3` path preserves only the chat/display warning, but drops the standalone Step 2b.5 behavior that records `check-plan-size.validation.log` and appends a warning to `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror Step 2b.5 rc 2/3 handling in the driver: write capture to check-plan-size.validation.log, call append-tool-failure.sh, then WARN and exit 0; document in design-postplan-emit.md
  - From Codex-Arch: In design-postplan-emit.sh --with-plan-size, reuse the existing Step 2b.5 append-tool-failure logging path for check-plan-size rc 2 and rc 3 before returning cleanly
  - From Codex-Requirements: Add the same check-plan-size.validation.log plus append-tool-failure Warnings write in the driver rc2/rc3 path, and extend the nonfatal harness case to assert it


### FINDING_4: Gate A re-entry merged caller is not structurally pinned
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Structure tests pin only three merged `--with-plan-size` call sites, leaving the Step 1e Gate A optional-trailer re-entry path free to regress back to the old fat file-first parsing shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add assert_thin_fence or contains pin for the Gate A re-entry block with --with-plan-size and rc arms, alongside the three existing site pins


### FINDING_5: Thin `rc 1` handling loses failure-specific status/messages
- **Reviewer(s)**: Codex-Arch, Codex-Edge
- **Severity**: important
- **Concern**: The proposed thin fence sees only `rc=1` while `design-postplan-emit.sh` multiplexes distinct failures onto exit 1, so existing targeted abort messages for missing diff lines, snapshot failures, emit failures, or validator infrastructure failures may be lost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep a minimal rc1-only status read, add distinct failure exit codes, or make the driver emit the existing human-readable failure line before exit 1 in --with-plan-size mode
  - From Codex-Edge: Either have --with-plan-size emit the existing rc1 human failure messages before exit 1, or keep a minimal rc1-only result-env read for POSTPLAN_EMIT_STATUS; add with-plan-size tests for the rc1 subcases.


### FINDING_6: `rc10` fix-and-retry can bypass the merged plan-size gate
- **Reviewer(s)**: Codex-Edge, Codex-dyn-exit-code-contract
- **Severity**: important
- **Concern**: When the merged driver exits `rc10` for validator defects before running plan-size, the existing fix-and-retry body may rerun raw emit/validation and then continue without applying the hard-size or partition handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update the rc10 contract so Fix-and-retry reruns the same site's design-postplan-emit.sh --with-plan-size driver and dispatches its rc again, or explicitly runs retained Step 2b.5 after validation succeeds.
  - From Codex-dyn-exit-code-contract: Revise the shared body or each rc10 arm so Fix-and-retry re-enters the same site-specific design-postplan-emit.sh --with-plan-size fence and Override runs the retained standalone Step 2b.5 before proceeding


### FINDING_7: Retained Step 2b.5 hard prompt must be site-aware
- **Reviewer(s)**: Codex-dyn-exit-code-contract, Codex-dyn-prompt-flow-sync
- **Severity**: important
- **Concern**: Retained standalone Step 2b.5 hard-size handling still appears to use the initial Split/Cancel prompt, but Gate B and plan-review-loop routes require Split/Override/Cancel semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-exit-code-contract: Keep the minimum change by documenting/coding two named hard-prompt bodies: initial/discussion use Split/Cancel, while Gate B and Step 3 plan-size-trigger retained callers use Split/Override/Cancel before continuing their surrounding flow
  - From Codex-dyn-prompt-flow-sync: Specify that Override-after-defects and Step 3 plan-size-trigger invoke the correct site hard prompt: Gate B / plan-review-loop get Split/Override/Cancel; initial Step 2b and discussion-round2 keep Split/Cancel.


### FINDING_8: `--with-plan-size` tests miss classification WARN display behavior
- **Reviewer(s)**: Codex-dyn-shell-io-contract
- **Severity**: important
- **Concern**: Existing tests do not cover classification-stderr warnings through the new display-only channel, so `--with-plan-size` could drop the warning or leak `WARN=`/KV output while current clean and plan-size failure cases still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-shell-io-contract: Add one --with-plan-size classification-warning fixture, reusing the missing/invalid run-params setup, asserting the warning body appears in stdout, stdout has no full-line KEY=VALUE or WARN= leakage, and .design-postplan-emit-result.env still contains WARN= for diagnostics


### FINDING_9: `check-plan-size.md` caller docs omit direct plan-review-loop caller
- **Reviewer(s)**: Codex-dyn-prompt-flow-sync
- **Severity**: latent
- **Concern**: The docs update adds the new driver caller but still omits `plan-review-loop.sh`, which directly calls `check-plan-size.sh`; future edits could miss that retained caller.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-prompt-flow-sync: Add plan-review-loop.sh to the callers / edit-in-sync list alongside design-postplan-emit.sh --with-plan-size.### OOS_1:
- **Description**: Step 3.5 prose still says Gate B requires Step 2b.5 immediately after each settled design-postplan-emit.sh re-emit. Scenario: After merge, operators and agents may follow stale two-call sequencing at Gate B despite approval-gates rewrite
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1154
- **Phase**: design


