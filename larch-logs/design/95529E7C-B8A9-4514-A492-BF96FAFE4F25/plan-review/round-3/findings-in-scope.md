### FINDING_1: Pause publish fail-closed gate would skip recovery-branch resume path
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-dyn-state-machine, Cursor-dyn-contract-sync, Codex-dyn-contract-sync
- **Severity**: important
- **Concern**: Multiple reviewers report that broadening `design-pause-save.sh` to fail on any non-zero `design-log-publish.sh` exit would incorrectly bypass the existing `PUBLISH_OK=false` + `RECOVERY_BRANCH` recovery path. That path is currently used for post-push publish failures where a resumable pause marker should still be written with `LOG_RECOVERY_BRANCH`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Narrow the new gate to the contradictory envelope only (e.g. publish_rc -ne 0 and PUBLISH_OK=true), or only when PUBLISH_OK is empty; leave publish_rc -ne 0 with PUBLISH_OK=false on the existing recovery branch. Extend test-design-pause-resume.sh recovery stub to exit 1 so regression is caught
  - From Codex-Arch: Limit the new fail-closed check to contradictory or missing envelopes, e.g. fail when publish_rc is non-zero and PUBLISH_OK is true or empty, but keep the existing PUBLISH_OK=false plus RECOVERY_BRANCH branch for pause recovery
  - From Codex-Edge: Fail closed only for contradictory or missing envelopes, e.g. publish_rc non-zero with PUBLISH_OK=true or empty. Preserve the current PUBLISH_OK=false plus valid RECOVERY_BRANCH path so pause recovery still works.
  - From Codex-Innovation: Only fail closed for contradictory PUBLISH_OK=true on non-zero exit, or normalize that case to PUBLISH_OK=false and let the existing PUBLISH_OK != true recovery branch run; add a pause-save test where recovery output exits 1 and still writes the recovery marker
  - From Cursor-Pragmatic: Narrow the gate to match `design-publish.sh`: force `PUBLISH_OK=false` when `publish_rc != 0` and stdout says `true`, keep `emit_fail "publish-failed"` only for non-zero exit with no `PUBLISH_OK` line; let exit 1 + `PUBLISH_OK=false` + recovery metadata fall through to the existing recovery branches; extend `test-design-pause-resume.sh` with an exit-1 + `PUBLISH_OK=false` + `RECOVERY_BRANCH` case so regression is caught
  - From Codex-Pragmatic: Only fail closed on contradictory success, e.g. if publish_rc is non-zero and PUBLISH_OK is true then force PUBLISH_OK=false and log the failure; preserve the existing RECOVERY_BRANCH handling for PUBLISH_OK=false so recovery-only pause markers remain resumable
  - From Codex-dyn-state-machine: Narrow the new gate to contradictory stdout success, e.g. publish_rc non-zero with PUBLISH_OK=true forces failure, while preserving the existing non-zero plus empty PUBLISH_OK failure and PUBLISH_OK=false plus RECOVERY_BRANCH marker path; add a regression where rc=1 with PUBLISH_OK=false and RECOVERY_BRANCH still yields PAUSE_OK=true.
  - From Cursor-dyn-contract-sync: Narrow the gate to the contradictory envelope only, e.g. `publish_rc -ne 0 && ( -z PUBLISH_OK || PUBLISH_OK == true )`, so exit 1 + `PUBLISH_OK=false` + `RECOVERY_BRANCH` still reaches the existing recovery branch. Extend `test-design-pause-resume.sh` with a stub mode that prints `PUBLISH_OK=false` + `RECOVERY_BRANCH` and exits 1 to lock the production contract.
  - From Codex-dyn-contract-sync: Narrow the immediate fail-closed gate to non-zero with missing PUBLISH_OK or contradictory PUBLISH_OK=true; preserve the existing PUBLISH_OK=false plus RECOVERY_BRANCH handling and add a regression case for exit 1 false recovery branch plus the contradictory true case

### FINDING_2: Clarify publish parity is targeted at wrong Step 0b sub-step
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-state-machine, Cursor-dyn-callsite-boundaries
- **Severity**: important
- **Concern**: The plan appears to target Step 0b sub-step 3.5/rename wording for FINDING_17 parity, but publish parsing lives in sub-step 3. If implemented literally, non-zero `design-log-publish.sh` exits with stdout `PUBLISH_OK=true` may still allow the rename gate to proceed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Retarget the SKILL.md edit to clarify loop sub-step 3.3 (publish bullet ~line 463): after parsing stdout, any non-zero _publish_rc must force PUBLISH_OK=false and record the warning before sub-step 3.5 rename; pin the structural test to that bullet (e.g. grep the step-0b block for the rule before tracking-issue-write.sh rename)
  - From Cursor-dyn-state-machine: Edit clarify substep 3 publish prose (line 463): after parsing stdout, any non-zero `_publish_rc` must force `PUBLISH_OK=false`, append the failure log, and warn — matching Step 5c/`design-publish.sh`. Keep substep 5 rename gate unchanged. Point `test-design-structure.sh` assertion at that substep 3 text (not only before-rename wording near substep 5)
  - From Cursor-dyn-callsite-boundaries: Retarget the plan/SKILL edit to clarify sub-step 3 (the design-log-publish fence). Pin the structural grep to that sub-step, not 3.5

### FINDING_3: Script test change lacks sibling contract doc update
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan updates `test-design-pause-resume.sh` but does not update its sibling `.md` contract documentation, despite the repository rule requiring sibling docs for changed shell scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add an UPDATED entry for skills/design/scripts/test-design-pause-resume.md documenting the rc-ok-false publish stub case and expected PAUSE_OK=false / publish-failed / no marker behavior

### FINDING_4: Pause-save validates repo too late for direct malformed --repo inputs
- **Reviewer(s)**: Codex-dyn-callsite-boundaries
- **Severity**: important
- **Concern**: The plan relies on `design-log-publish.sh` repo validation, but `design-pause-save.sh` uses `REPO` earlier for `gh issue view` and state handling. A malformed direct `--repo` may therefore fail with poor diagnostics or enter malformed state before publish validation can reject it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-callsite-boundaries: Add the same validate_repo guard in design-pause-save.sh before building gh_repo_args or state, return a clear invalid-repo failure, and cover that direct malformed --repo pause-save case in the planned pause-resume test/docs
