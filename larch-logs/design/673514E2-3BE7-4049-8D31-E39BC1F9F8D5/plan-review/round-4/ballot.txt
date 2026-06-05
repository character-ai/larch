### FINDING_1: Cancel side-effect order is contradictory
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Cancel handling has conflicting ordering requirements: one section says reject banner first then render, while route-specific bullets say render then reject. Implementers could emit the final summary before the required Bash stderr rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make lines 59-60 match line 34: after result-env write, emit reject via `larch_err`/`larch_errf`, then command-scoped render, then stdout KV emit and `exit 0`

### FINDING_2: Cancel routes are not stated as unconditional post-fence aborts
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan ties abort behavior to non-empty final-summary emission rather than making cancel-title-filter and cancel-reentry-guard unconditional stops before sub-step 3. If render fails or produces an empty file, an orchestrator may continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State one rule: for those two `ROUTE` values, **always** stop `/design` before sub-step 3; verbatim summary emit only when `[ -s … ]`. Pin that in post-fence prose and in `scripts/test-design-structure.sh` (not only the `-s` gate).

### FINDING_3: Resume env refresh migration can drop identity/repo forwarding and route pins
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Cursor-dyn-pin-migration, Codex-dyn-pin-migration
- **Severity**: important
- **Concern**: Moving resume `write-design-current-env.sh` into `design-route.sh` deletes or weakens existing SKILL.md pins without clearly preserving the full forwarded identity: issue number, Claude PID, repo, and the resume argv/helper shape. This can break non-default repo resumes or concurrent session isolation while tests still pass on unrelated literals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the full current identity forwarding to the design-route.sh resume branch: --issue-number "$ISSUE", --claude-pid "$CLAUDE_PID", and [[ -n "$REPO" ]] && _wdce_resume_args+=(--repo "$REPO"); add matching DESIGN_ROUTE_SH pins when deleting the SKILL.md pins
  - From Codex-Pragmatic: When moving _wdce_resume_args into skills/design/scripts/design-route.sh, preserve ${REPO:+--repo "$REPO"} on write-design-current-env.sh and add a DESIGN_ROUTE_SH structural pin for it.
  - From Cursor-dyn-pin-migration: Add `grep -Fq` pins on `$DESIGN_ROUTE_SH` for `_wdce_resume_args` (or equivalent argv array) and `${REPO:+--repo "$REPO"}` on the resume `write-design-current-env.sh` invocation; drop the step0b_block-only checks
  - From Codex-dyn-pin-migration: Add DESIGN_ROUTE_SH pins scoped to the resume path for write-design-current-env.sh and repo forwarding, for example _wdce_resume_args+=(--repo "$REPO") or ${REPO:+--repo "$REPO"}, and retarget the Check 21 resume-refresh assertion away from SKILL_MD.

### FINDING_4: Init env-refresh child lacks quiet stderr bridge
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Codex-dyn-quiet-channel
- **Severity**: important
- **Concern**: The init `write-design-current-env.sh` child is required to surface diagnostics through the quiet stderr bridge, but the plan only adds failure banners and does not wrap the init invocation with the `LARCH_QUIET_PID` / FD 4 conditional. Under quiet mode, actionable child diagnostics can be swallowed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Under quiet init, write-design-current-env.sh diagnostics during Step 0b init env-refresh are swallowed while the moved banner tells the operator to inspect those diagnostics; resume failures get the bridge but init failures do not Add the same quiet predicate and 2>&4 redirect to design-init-runparams.sh wdce call, document it in design-init-runparams.md, and pin the predicate in test-design-structure.sh alongside the env-refresh-failed banner migration
  - From Codex-Requirements: Add the same LARCH_QUIET_PID == $$ fd4 predicate around the init _wdce_args invocation, or explicitly pin that behavior in design-init-runparams.sh and scripts/test-design-structure.sh
  - From Codex-dyn-quiet-channel: Extend the design-init-runparams.sh step to invoke _wdce_args with the same conditional form: if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then ... >/dev/null 2>&4; else ... >/dev/null; fi, then keep the moved larch_err failure banner

### FINDING_5: Cancel reentry guard may lose N/A fallback when run-params.json is absent
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Moving cancel-reentry-guard rendering into the driver does not preserve the current tolerant `N/A` fallback for missing `run-params.json`, missing `jq`, or jq failure. A fresh re-entry guard can occur before Step 0b creates run params, so strict jq under `set -e` can abort before emitting the route/result/summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Specify SUMMARY_MODE_STRING defaults to N/A, only jq when run-params.json exists and jq is available, tolerate jq failure with N/A, and make the cancel-reentry smoke cover missing run-params.json

### FINDING_6: Contract-drift test pins are too broad
- **Reviewer(s)**: Codex-dyn-pin-migration
- **Severity**: latent
- **Concern**: The proposed migration uses independent file-wide contains checks for literals that already appear in an unrelated fallback warning. Tests could pass even if the intended moved `larch_err` banner omits key repro-command text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-pin-migration: Scope the three contract-drift pins to the same larch_err line/block, or pin one longer moved banner literal that includes contract drift, aborting before silent tier downgrade, and bash scripts/test-write-run-params.sh.

### FINDING_7: Quiet-channel examples and resume pins allow invalid FD 4 usage
- **Reviewer(s)**: Cursor-dyn-quiet-channel, Codex-dyn-quiet-channel
- **Severity**: important
- **Concern**: The command-scoped render/resume examples and pins do not require the full quiet-mode conditional. Copying unconditional `>/dev/null 2>&4` can mis-route diagnostics when quiet is disabled and FD 4 is not open; tests may also pass while resume diagnostics remain hidden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-quiet-channel: Replace the example with the full `emit_diag`-style if/else from `scripts/render-run-summary.sh:12-17` (quiet: `>/dev/null 2>&4`; else: `>/dev/null` only) and apply the same pattern to resume `write-design-current-env.sh`
  - From Codex-dyn-quiet-channel: Add a no-comment-only $DESIGN_ROUTE_SH pin tying write-design-current-env.sh to the exact literal [ "${LARCH_QUIET_PID:-}" = "$$" ] and 2>&4, analogous to the render-final-summary.sh pin

### FINDING_8: Post-fence ROUTE source is ambiguous or unavailable
- **Reviewer(s)**: Cursor-dyn-handoff-sequencing, Codex-dyn-handoff-sequencing
- **Severity**: important
- **Concern**: The plan says post-fence logic can bind `ROUTE` from result-env and/or merged stdout KVs, but driver stdout is captured inside the Bash fence and not available to the prompt-side post-fence block. Cancel-only emit/abort logic may never run, allowing silence or continuation into clarify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-handoff-sequencing: In SKILL.md post-fence prose and design-route.md orchestrator handoff, normatively require file-first ROUTE from $DESIGN_TMPDIR/.design-route-result.env via Read (allowlisted ROUTE= key, same symlink refusal as in-fence); drop merged stdout KVs as a post-fence source unless the fence adds an explicit ROUTE= echo; pin .design-route-result.env Read in test-design-structure.sh step0b_block
  - From Codex-dyn-handoff-sequencing: Tighten the proposed SKILL.md prose and test pin to say the post-fence block reads ROUTE from $DESIGN_TMPDIR/.design-route-result.env after the fence; keep stdout merge only as the in-fence parse fallback/validation unless the fence explicitly persists or prints a post-fence source.
