### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:175-178
- **Concern**: Proposed FINDING_17 parity broadens the gate to any non-zero publish_rc before recovery handling. Scenario: Post-push design-log-publish.sh failures exit 1 with PUBLISH_OK=false and RECOVERY_BRANCH on stdout; the plan forces emit_fail publish-failed immediately, skipping LOG_RECOVERY_BRANCH / WARN=recovery-branch-only and blocking a resumable pause marker
- **Proposed resolution**: Narrow the new gate to the contradictory envelope only (e.g. publish_rc -ne 0 and PUBLISH_OK=true), or only when PUBLISH_OK is empty; leave publish_rc -ne 0 with PUBLISH_OK=false on the existing recovery branch. Extend test-design-pause-resume.sh recovery stub to exit 1 so regression is caught

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/design-pause-save.sh:175-192
- **Concern**: Planned pause-path fail-closed gate bypasses the existing RECOVERY_BRANCH resume-marker path. Scenario: design-log-publish.sh intentionally exits 1 with PUBLISH_OK=false and RECOVERY_BRANCH after post-push failures; changing the first gate to any non-zero publish_rc makes design-pause-save emit publish-failed before recording LOG_RECOVERY_BRANCH or writing the pause marker, so a recoverable pause snapshot is no longer resumable
- **Proposed resolution**: Limit the new fail-closed check to contradictory or missing envelopes, e.g. fail when publish_rc is non-zero and PUBLISH_OK is true or empty, but keep the existing PUBLISH_OK=false plus RECOVERY_BRANCH branch for pause recovery

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:463-465
- **Concern**: Plan targets Step 0b clarify sub-step 3.5 for FINDING_17 fail-closed publish parsing, but 3.5 is the rename gate, not publish. Scenario: Implementer follows the plan literally and adds the non-zero-exit ⇒ PUBLISH_OK=false rule to clarify sub-step 5 (rename) or leaves publish sub-step 3.3 unchanged; a non-zero design-log-publish.sh exit with stdout PUBLISH_OK=true can still allow rename while publish failed
- **Proposed resolution**: Retarget the SKILL.md edit to clarify loop sub-step 3.3 (publish bullet ~line 463): after parsing stdout, any non-zero _publish_rc must force PUBLISH_OK=false and record the warning before sub-step 3.5 rename; pin the structural test to that bullet (e.g. grep the step-0b block for the rule before tracking-issue-write.sh rename)

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:175-184
- **Concern**: Proposed publish_rc gate would bypass the existing recovery-branch pause path. Scenario: design-log-publish.sh documents post-push failures as exit 1 with PUBLISH_OK=false and RECOVERY_BRANCH. Changing this gate to fail on any non-zero exit makes pause-save emit publish-failed before it can persist LOG_RECOVERY_BRANCH and write the pause marker, so a recoverable pushed-branch pause becomes unrecoverable.
- **Proposed resolution**: Fail closed only for contradictory or missing envelopes, e.g. publish_rc non-zero with PUBLISH_OK=true or empty. Preserve the current PUBLISH_OK=false plus valid RECOVERY_BRANCH path so pause recovery still works.

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:175-187
- **Concern**: Proposed broad non-zero publish gate would bypass existing recovery-branch handling. Scenario: design-log-publish.sh can emit PUBLISH_OK=false plus RECOVERY_BRANCH and exit 1 after push/merge failures; the plan's if publish_rc != 0 change would return PAUSE_OK=false before writing the pause marker, so a resumable pause becomes a failed save
- **Proposed resolution**: Only fail closed for contradictory PUBLISH_OK=true on non-zero exit, or normalize that case to PUBLISH_OK=false and let the existing PUBLISH_OK != true recovery branch run; add a pause-save test where recovery output exits 1 and still writes the recovery marker

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:175-178
- **Concern**: Broadening the publish gate to `if [[ "$publish_rc" -ne 0 ]]` calls `emit_fail "publish-failed"` for every non-zero exit, but real `design-log-publish.sh` post-push failures legitimately exit 1 with `PUBLISH_OK=false` and `RECOVERY_BRANCH` on stdout. Scenario: Pause during a post-push publish failure (exit 1, honest `PUBLISH_OK=false`, recovery branch present) would abort with `PAUSE_OK=false` / `ERROR=publish-failed` instead of today's recovery-only path (`PAUSE_OK=true`, `WARN=recovery-branch-only`, marker written with `LOG_RECOVERY_BRANCH`) — contradicts the plan edge-case claim that only the contradictory stdout-true case is newly blocked
- **Proposed resolution**: Narrow the gate to match `design-publish.sh`: force `PUBLISH_OK=false` when `publish_rc != 0` and stdout says `true`, keep `emit_fail "publish-failed"` only for non-zero exit with no `PUBLISH_OK` line; let exit 1 + `PUBLISH_OK=false` + recovery metadata fall through to the existing recovery branches; extend `test-design-pause-resume.sh` with an exit-1 + `PUBLISH_OK=false` + `RECOVERY_BRANCH` case so regression is caught

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:175-190
- **Concern**: Proposed pause publish gate treats every non-zero design-log-publish exit as hard publish-failed. Scenario: design-log-publish.sh intentionally exits 1 after post-push failures while emitting PUBLISH_OK=false and RECOVERY_BRANCH; current pause-save records LOG_RECOVERY_BRANCH and writes a resumable marker, but the proposed if [[ "$publish_rc" -ne 0 ]] would skip that recovery path and break pause/resume after a pushed-but-unmerged snapshot
- **Proposed resolution**: Only fail closed on contradictory success, e.g. if publish_rc is non-zero and PUBLISH_OK is true then force PUBLISH_OK=false and log the failure; preserve the existing RECOVERY_BRANCH handling for PUBLISH_OK=false so recovery-only pause markers remain resumable

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/scripts/test-design-pause-resume.md:1-9
- **Concern**: Plan updates test-design-pause-resume.sh but omits its sibling contract doc despite the stated every changed .sh gets sibling .md updated constraint. Scenario: The new pause publish regression can land undocumented, violating the script-md-siblings rule and risking lint/relevant-check failures
- **Proposed resolution**: Add an UPDATED entry for skills/design/scripts/test-design-pause-resume.md documenting the rc-ok-false publish stub case and expected PAUSE_OK=false / publish-failed / no marker behavior

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-state-machine
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:463-465
- **Concern**: Plan targets FINDING_17 clarify parity at Step 0b substep 3.5 but publish parsing lives in substep 3. Scenario: Clarify substep 3 (`skills/design/SKILL.md:463`) still only treats non-zero `design-log-publish.sh` exit as failure when stdout lacks `PUBLISH_OK=`; rename substep 5 (`:465`) already gates on `PUBLISH_OK=true`. If implementers follow the plan literally and only add prose near substep 5, stdout `PUBLISH_OK=true` on a non-zero exit can still satisfy the rename gate and run `tracking-issue-write.sh --state designing` despite a failed publish
- **Proposed resolution**: Edit clarify substep 3 publish prose (line 463): after parsing stdout, any non-zero `_publish_rc` must force `PUBLISH_OK=false`, append the failure log, and warn — matching Step 5c/`design-publish.sh`. Keep substep 5 rename gate unchanged. Point `test-design-structure.sh` assertion at that substep 3 text (not only before-rename wording near substep 5)

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-state-machine
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:172-191; scripts/design-log-publish.sh:926-929; scripts/design-pause-save.md:32-41
- **Concern**: The proposed pause-save change treats every non-zero publish exit as publish-failed before the existing RECOVERY_BRANCH path can run.. Scenario: Post-push design-log-publish failures intentionally exit 1 with PUBLISH_OK=false and RECOVERY_BRANCH; current pause-save records LOG_RECOVERY_BRANCH and writes a resumable pause marker, but the planned broad gate would skip that marker and leave resume without the recovery pointer.
- **Proposed resolution**: Narrow the new gate to contradictory stdout success, e.g. publish_rc non-zero with PUBLISH_OK=true forces failure, while preserving the existing non-zero plus empty PUBLISH_OK failure and PUBLISH_OK=false plus RECOVERY_BRANCH marker path; add a regression where rc=1 with PUBLISH_OK=false and RECOVERY_BRANCH still yields PAUSE_OK=true.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:175-178
- **Concern**: Broadening the publish gate to `publish_rc -ne 0` aborts before recovery handling. Scenario: `design-log-publish.sh` documents post-push failures as exit 1 with `PUBLISH_OK=false` and optional `RECOVERY_BRANCH` (scripts/design-log-publish.sh:14-16, scripts/design-log-publish.md:124-131). Today pause-save only short-circuits when `publish_rc -ne 0 && -z PUBLISH_OK`, then the `PUBLISH_OK != true` branch records `LOG_RECOVERY_BRANCH` and can still emit `PAUSE_OK=true` (scripts/design-pause-save.sh:180-191; scripts/design-pause-save.md:32-38). The plan replaces that with unconditional `emit_fail publish-failed` on any non-zero exit, which blocks the recovery path for real merge/CI/push failures. The plan edge-case note claiming recovery still works on exit 0 only is wrong for production; the new `rc-ok-false` stub exits 0 and would not catch this.
- **Proposed resolution**: Narrow the gate to the contradictory envelope only, e.g. `publish_rc -ne 0 && ( -z PUBLISH_OK || PUBLISH_OK == true )`, so exit 1 + `PUBLISH_OK=false` + `RECOVERY_BRANCH` still reaches the existing recovery branch. Extend `test-design-pause-resume.sh` with a stub mode that prints `PUBLISH_OK=false` + `RECOVERY_BRANCH` and exits 1 to lock the production contract.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:175-191; scripts/design-pause-save.md:32-41; scripts/design-log-publish.md:124-131
- **Concern**: Planned pause-save change treats every non-zero publish exit as publish-failed before parsing documented recovery metadata. Scenario: When design-log-publish exits 1 after push/CI/merge failure with PUBLISH_OK=false and RECOVERY_BRANCH, the proposed broad gate would skip the existing LOG_RECOVERY_BRANCH marker path, so pause/resume loses the recoverable snapshot despite the documented contract
- **Proposed resolution**: Narrow the immediate fail-closed gate to non-zero with missing PUBLISH_OK or contradictory PUBLISH_OK=true; preserve the existing PUBLISH_OK=false plus RECOVERY_BRANCH handling and add a regression case for exit 1 false recovery branch plus the contradictory true case

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-callsite-boundaries
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:463-465
- **Concern**: Step 0b clarify FINDING_17 parity is aimed at the wrong sub-step label (plan says 3.5; publish is sub-step 3). Scenario: An implementer can edit Step 5c prose or skip the clarify publish block, leaving non-zero exit + stdout PUBLISH_OK=true able to satisfy rename gates
- **Proposed resolution**: Retarget the plan/SKILL edit to clarify sub-step 3 (the design-log-publish fence). Pin the structural grep to that sub-step, not 3.5

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-callsite-boundaries
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-pause-save.sh:18-25,106-123,157-165; plan.txt:30-35
- **Concern**: The plan says design-pause-save.sh resolves/validates REPO before forwarding --repo, but resolve_repo echoes caller input and the script uses REPO in gh issue view before design-log-publish.sh can reject it. Scenario: A pause save invoked with malformed --repo, including newline or traversal-shaped values, fails at the issue-body read path with poor diagnostics or writes malformed REPO into pause state; the proposed design-log-publish.sh fail-closed validation is never reached
- **Proposed resolution**: Add the same validate_repo guard in design-pause-save.sh before building gh_repo_args or state, return a clear invalid-repo failure, and cover that direct malformed --repo pause-save case in the planned pause-resume test/docs
