### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.sh:40-85
- **Concern**: skills/design/SKILL.md Step 3 will have three pause-save guards but assert_thin_fence only checks the first. Scenario: A preview or captured --no-preview guard can omit ${REPO:+--repo "$REPO"} while timing-ledger REPO threading still passes assert_thin_fence and the timing-ledger pin
- **Proposed resolution**: Pin REPO on every Step 3 design-pause-save.sh line in the step:3..step:3.5 region (or extend assert_thin_fence to require REPO on all pause-save lines in scoped regions with multiple fences)

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-step3-review-cap.sh:57-64; scripts/test-design-multi-round-integration.sh:498-500
- **Concern**: Plan prefers requiring an explicit --preview-only/--no-preview mode but does not update all direct run-step3-review.sh callers. Scenario: Implementing the stricter parser would make existing cap and multi-round integration harnesses call the driver without a mode flag and fail before review logic runs
- **Proposed resolution**: For minimum change, keep omitted mode as --no-preview; otherwise add --no-preview to these direct harness calls and document that compatibility break explicitly

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:86-96; skills/design/scripts/emit-design-plan-preview.sh:99-104
- **Concern**: Preview driver skips renderer whenever .step3-entry-plan-printed exists, but the current renderer validates the allowlist before that sentinel check. Scenario: A stale sentinel in a disallowed DESIGN_TMPDIR suppresses the allowlist warning; the following --no-preview path can then run/write in that tmpdir with no visible warning, regressing the SECURITY.md allowlist-before-sentinel contract
- **Proposed resolution**: Before suppressing on an existing sentinel, make --preview-only perform the same missing/invalid and larch_design_tmpdir_validate warning checks, or otherwise preserve the existing allowlist-warning-before-sentinel behavior; add the sentinel-present disallowed-tmpdir case to test-run-step3-review.sh

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/run-step3-review.sh (new --preview-only sentinel touch)
- **Concern**: Preview sentinel touch is gated only by renderer stdout, so the RUN_STEP3_EMIT_PREVIEW_SH seam can bypass the design-tmpdir allowlist. Scenario: A stub or mis-set seam prints ## Plan Candidate for Review while --design-tmpdir points outside the allowed session/tmp roots; the driver then writes .step3-entry-plan-printed there, violating the SECURITY.md allowlist/write contract
- **Proposed resolution**: After renderer output matches the touch string, validate the raw design tmpdir with scripts/lib-design-tmpdir.sh before touch; still call the renderer before validation to preserve live warning behavior

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-step3-review-cap.sh:58-64; scripts/test-design-multi-round-integration.sh:499-501
- **Concern**: Mode-flag plan is ambiguous while existing direct harness callers still invoke run-step3-review.sh without --no-preview. Scenario: If the implementation follows the plan's explicit-mode preference, these unlisted callers fail argv validation in CI despite being unchanged behavior paths
- **Proposed resolution**: Keep no mode as a backward-compatible --no-preview default, or add --no-preview to every direct run-step3-review.sh harness caller in the same plan

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/run-step3-review.sh:67-72
- **Concern**: Mode-flag default is ambiguous for non-SKILL callers. Scenario: Plan text both prefers requiring exactly one of --preview-only/--no-preview and only conditionally keeps --no-preview when neither is passed. test-run-step3-review.sh and scripts/test-design-multi-round-integration.sh:498-500 invoke the driver with --design-tmpdir and --round-cap only (no mode flag). Requiring a mode flag without a default breaks those harnesses and make lint step 7.
- **Proposed resolution**: In the run-step3-review.sh section, state explicitly: when neither mode flag is passed, behave as --no-preview. Require explicit --preview-only/--no-preview only on SKILL.md fences; optionally add --no-preview to the integration harness call for clarity.

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-step3-review-cap.sh:57-64; scripts/test-design-multi-round-integration.sh:498-500
- **Concern**: Plan may require a mode flag for run-step3-review.sh without updating existing direct callers. Scenario: These harnesses still invoke run-step3-review.sh with only --design-tmpdir and --round-cap; if the implementation follows the plan's "prefer requiring exactly one mode flag" wording, make lint/test shards will fail despite unchanged review behavior
- **Proposed resolution**: Preserve no-flag as --no-preview for backward compatibility, or explicitly add --no-preview to every existing direct harness/CLI caller in the plan

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/feature-description.txt:7-11; <TMPDIR>/plan.txt:5-17
- **Concern**: Plan keeps a separate live preview-only driver fence and defers the per-Step-3-entry turn reduction even though the feature says to make the preview the first action inside run-step3-review.sh and remove the separate preview turn. Scenario: The PR would transfer sentinel ownership but still spend the extra Step 3 Bash turn on every re-entry, so it does not satisfy the stated Change/Why
- **Proposed resolution**: Revise the Phase 2 acceptance to say turn reduction is explicitly deferred, or implement a single driver invocation that streams the preview before review without a second Step 3 fence

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:86-95; SECURITY.md:121
- **Concern**: The new sentinel writer is not required to validate --design-tmpdir before touching .step3-entry-plan-printed. Scenario: The preview path passes the raw tmpdir to a renderer seam and touches based on output text; a bad override or renderer bug could write the sentinel outside the allowlisted session/tmp roots
- **Proposed resolution**: Before any sentinel read/write in --preview-only, require an existing directory that passes larch_design_tmpdir_validate, while still allowing the renderer warning to print live

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:69-72; scripts/test-design-multi-round-integration.sh:498-500; skills/design/scripts/test-step3-review-cap.sh:57-64
- **Concern**: The mode-flag contract is ambiguous and the plan does not enumerate existing direct run-step3-review.sh callers. Scenario: If the implementer requires exactly one mode flag, current harness callers without --no-preview break; if they preserve the default, the “prefer requiring exactly one” instruction is ignored
- **Proposed resolution**: For the minimum-change path, specify that omitted mode remains --no-preview for backward compatibility, while SKILL.md uses explicit --preview-only and --no-preview

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-scope-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/issue-anchored-plan.md:189-194
- **Concern**: Step 6 drift sweep names this file but Files to modify/create omits it. Scenario: The normative wire doc will still tell operators/auditors that Step 3 preview is a direct emit-design-plan-preview.sh SKILL.md invocation after the refactor
- **Proposed resolution**: Add ### UPDATED: docs/issue-anchored-plan.md to the file list (or drop it from step 6) and rewrite lines 189-194 to describe live run-step3-review.sh --preview-only before captured --no-preview, with emit-design-plan-preview.sh as the renderer only

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-scope-drift
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/issue-anchored-plan.md:189-194; plan.txt:63-260,281-284
- **Concern**: docs/issue-anchored-plan.md is named in the Step 6 drift sweep but is missing from Files to modify/create, even though it currently describes Step 3 preview behavior as the emit-design-plan-preview.sh invocation wired in SKILL.md.. Scenario: If implementers follow the explicit file list or scope-files, this drift target can be skipped, leaving normative docs that contradict the proposed driver-owned run-step3-review.sh --preview-only flow.
- **Proposed resolution**: Add docs/issue-anchored-plan.md to the UPDATED file list with a minimal note to change the Step 3 preview sentence to the new driver-owned preview flow, or remove it from the drift sweep only if the stale wording is intentionally left unchanged.
