### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:34,59-60
- **Concern**: Cancel side-effect order contradicts itself: `route_emit_cancel_side_effects` lists reject `larch_err`/`larch_errf` then render, but cancel-title-filter / cancel-reentry-guard bullets say render + reject. Scenario: Implementer follows the Files bullets and runs `render-final-summary.sh` before reject banners, breaking the mandatory operator order (reject stderr during Bash first, verbatim summary in chat second) at plan.txt:17
- **Proposed resolution**: Make lines 59-60 match line 34: after result-env write, emit reject via `larch_err`/`larch_errf`, then command-scoped render, then stdout KV emit and `exit 0`

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:83-86; plan.txt:109-110
- **Concern**: Post-fence cancel abort is tied to the non-empty `final-summary.md` emit bullet, not stated as unconditional for `cancel-title-filter` / `cancel-reentry-guard`. Scenario: `render-final-summary.sh` is wrapped with `|| true`; if render fails or leaves an empty file, the `[ -s … ]` gate skips chat emit and an orchestrator can treat the list as “emit when possible” and continue into sub-step 3 (clarify) even though the fence now exits 0
- **Proposed resolution**: State one rule: for those two `ROUTE` values, **always** stop `/design` before sub-step 3; verbatim summary emit only when `[ -s … ]`. Pin that in post-fence prose and in `scripts/test-design-structure.sh` (not only the `-s` gate).

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:428-438
- **Concern**: Plan moves resume write-design-current-env.sh into design-route.sh but only calls out SESSION_ID and manual_gate_b, while the current inline invocation also forwards issue number, claude pid, and REPO. Scenario: Resume from a non-default repo or concurrent Claude session can refresh source-env without REPO or the PID-scoped symlink, causing later resumed steps to use the hub default repo or legacy global current-design-env.sh
- **Proposed resolution**: Add the full current identity forwarding to the design-route.sh resume branch: --issue-number "$ISSUE", --claude-pid "$CLAUDE_PID", and [[ -n "$REPO" ]] && _wdce_resume_args+=(--repo "$REPO"); add matching DESIGN_ROUTE_SH pins when deleting the SKILL.md pins

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:428-438
- **Concern**: Resume env refresh currently forwards ${REPO:+--repo "$REPO"}, but the plan moves the call into design-route.sh and explicitly deletes the SKILL.md repo pin without adding a design-route.sh replacement.. Scenario: A paused /design run against a non-default --repo can resume, refresh source-env.sh without REPO, and send later GitHub reads/writes to the default repository.
- **Proposed resolution**: When moving _wdce_resume_args into skills/design/scripts/design-route.sh, preserve ${REPO:+--repo "$REPO"} on write-design-current-env.sh and add a DESIGN_ROUTE_SH structural pin for it.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-init-runparams.sh:163-184
- **Concern**: Quiet stderr bridge omitted for init env-refresh child. Scenario: The plan requires every write-design-current-env.sh child to use the LARCH_QUIET_PID 2>&4 bridge (plan.txt:19-25) and pins it for resume in design-route.sh, but the design-init-runparams.sh section only adds larch_err banners and never wraps the existing wdce invocation with the quiet predicate
- **Proposed resolution**: Under quiet init, write-design-current-env.sh diagnostics during Step 0b init env-refresh are swallowed while the moved banner tells the operator to inspect those diagnostics; resume failures get the bridge but init failures do not Add the same quiet predicate and 2>&4 redirect to design-init-runparams.sh wdce call, document it in design-init-runparams.md, and pin the predicate in test-design-structure.sh alongside the env-refresh-failed banner migration

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:300-304
- **Concern**: Plan moves cancel-reentry-guard rendering into the driver but does not require the current N/A fallback when run-params.json is missing or jq fails. Scenario: Fresh re-entry guard routing runs before Step 0b creates run-params.json in the new tmpdir; a literal jq read under set -e can abort before ROUTE=cancel-reentry-guard, result-env, or summary render, so one of the seven preserved routes breaks
- **Proposed resolution**: Specify SUMMARY_MODE_STRING defaults to N/A, only jq when run-params.json exists and jq is available, tolerate jq failure with N/A, and make the cancel-reentry smoke cover missing run-params.json

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-init-runparams.sh:163-184
- **Concern**: Quiet stderr bridge is not planned for the init write-design-current-env.sh child despite the plan's quiet-driver MUST for write-design-current-env.sh child stderr. Scenario: Under larch_quiet_init, init env-refresh child diagnostics can stay in the quiet log instead of visible Bash stderr; the moved larch_err banner appears but the writer's actionable error can be lost
- **Proposed resolution**: Add the same LARCH_QUIET_PID == $$ fd4 predicate around the init _wdce_args invocation, or explicitly pin that behavior in design-init-runparams.sh and scripts/test-design-structure.sh

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1165-1173; plan.txt:92-93
- **Concern**: Resume pin migration deletes step0b_block checks for `_wdce_resume_args` and resume-scoped `${REPO:+--repo "$REPO"}` but the DESIGN_ROUTE_SH add-list omits equivalent driver pins. Scenario: After resume env refresh moves into design-route.sh, harness can pass while resume no longer threads REPO or builds the wdce args array
- **Proposed resolution**: Add `grep -Fq` pins on `$DESIGN_ROUTE_SH` for `_wdce_resume_args` (or equivalent argv array) and `${REPO:+--repo "$REPO"}` on the resume `write-design-current-env.sh` invocation; drop the step0b_block-only checks

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1165-1173,1363-1370; skills/design/SKILL.md:428-442; <TMPDIR>/plan.txt:89-97
- **Concern**: The resume pin migration deletes SKILL.md resume-refresh pins but does not add equivalent route pins for the actual write-design-current-env.sh helper call or repo forwarding.. Scenario: The moved resume refresh can drop ${REPO:+--repo "$REPO"} or even rely on an unpinned helper shape while Check 21's SKILL-wide write-design-current-env.sh grep still passes on unrelated clarify/init prose.
- **Proposed resolution**: Add DESIGN_ROUTE_SH pins scoped to the resume path for write-design-current-env.sh and repo forwarding, for example _wdce_resume_args+=(--repo "$REPO") or ${REPO:+--repo "$REPO"}, and retarget the Check 21 resume-refresh assertion away from SKILL_MD.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-pin-migration
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:359-361; skills/design/scripts/design-init-runparams.sh:236-240; <TMPDIR>/plan.txt:71-73,89-91
- **Concern**: The contract-drift migration proposes independent file-wide contains pins, but two migrated literals already exist in an unrelated design-init-runparams.sh fallback warning.. Scenario: A driver could add only aborting before silent tier downgrade to the new larch_err banner while omitting the repro command there; the contract drift and bash scripts/test-write-run-params.sh pins would still pass from the existing fallback warning.
- **Proposed resolution**: Scope the three contract-drift pins to the same larch_err line/block, or pin one longer moved banner literal that includes contract drift, aborting before silent tier downgrade, and bash scripts/test-write-run-params.sh.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-quiet-channel
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:47-52
- **Concern**: Command-scoped render example uses unconditional `>/dev/null 2>&4` with only a comment to adjust per quiet mode. Scenario: Implementers copying the snippet skip the `if [ "${LARCH_QUIET_PID:-}" = "$$" ]` branch; when quiet is disabled FD 4 is never opened and stderr is mis-routed, and harnesses using `LARCH_QUIET_DISABLE=1` can lose or misplace child diagnostics
- **Proposed resolution**: Replace the example with the full `emit_diag`-style if/else from `scripts/render-run-summary.sh:12-17` (quiet: `>/dev/null 2>&4`; else: `>/dev/null` only) and apply the same pattern to resume `write-design-current-env.sh`

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-quiet-channel
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-init-runparams.sh:163-176
- **Concern**: Plan moves the env-refresh-failed banner into design-init-runparams.sh but does not require the quiet bridge on its write-design-current-env.sh child. Scenario: After larch_quiet_init, the child inherits stdout and stderr redirected to quiet logs; on write-design-current-env.sh failure, child diagnostics can be hidden even though the moved larch_err banner tells the operator to inspect them
- **Proposed resolution**: Extend the design-init-runparams.sh step to invoke _wdce_args with the same conditional form: if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then ... >/dev/null 2>&4; else ... >/dev/null; fi, then keep the moved larch_err failure banner

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-quiet-channel
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1165-1173
- **Concern**: Planned resume pins do not pin the literal quiet predicate plus 2>&4 for the design-route.sh write-design-current-env.sh child. Scenario: An implementation could satisfy the planned _wdce_resume_rc, manual_gate_b, --manual-requested, and larch_err pins while omitting the bridge, silently dropping resume env-refresh child diagnostics under quiet mode
- **Proposed resolution**: Add a no-comment-only $DESIGN_ROUTE_SH pin tying write-design-current-env.sh to the exact literal [ "${LARCH_QUIET_PID:-}" = "$$" ] and 2>&4, analogous to the render-final-summary.sh pin

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-handoff-sequencing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:383-456 (planned post-fence prose per plan.txt:83-86)
- **Concern**: Post-fence ROUTE binding cites merged stdout KVs but driver stdout is captured only inside the subshell. Scenario: After cancel case bodies become no-ops and the route fence exits 0, ROUTE= is not echoed to Bash tool stdout (_route_out=$(design-route.sh) swallows driver KVs; fence only prints WARN/ERROR). Post-fence prose that says bind ROUTE from parsed result-env / merged stdout KVs leaves ROUTE undefined outside the fence, so the cancel-only emit+abort block may never run and final-summary.md stays silent
- **Proposed resolution**: In SKILL.md post-fence prose and design-route.md orchestrator handoff, normatively require file-first ROUTE from $DESIGN_TMPDIR/.design-route-result.env via Read (allowlisted ROUTE= key, same symlink refusal as in-fence); drop merged stdout KVs as a post-fence source unless the fence adds an explicit ROUTE= echo; pin .design-route-result.env Read in test-design-structure.sh step0b_block

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-handoff-sequencing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:327-378
- **Concern**: Post-fence ROUTE source is ambiguous: the plan says result-env and/or merged stdout KVs, but current Step 0b captures driver stdout into _route_out and does not print ROUTE; those merged shell variables disappear when the Bash fence exits.. Scenario: On cancel-title-filter or cancel-reentry-guard, the fence exits 0, but the post-fence orchestrator may try to rely on merged stdout KVs that are not available outside the Bash process, so it can skip the mandatory final-summary.md emit or continue into sub-step 3.
- **Proposed resolution**: Tighten the proposed SKILL.md prose and test pin to say the post-fence block reads ROUTE from $DESIGN_TMPDIR/.design-route-result.env after the fence; keep stdout merge only as the in-fence parse fallback/validation unless the fence explicitly persists or prints a post-fence source.
