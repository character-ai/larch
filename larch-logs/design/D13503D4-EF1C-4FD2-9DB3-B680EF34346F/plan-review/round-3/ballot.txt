### FINDING_1: Step 3 pause-save REPO assertions only cover the first guard
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned Step 3 changes add multiple `design-pause-save.sh` guard lines, but the existing `assert_thin_fence` coverage only verifies the first one. A later preview or captured `--no-preview` guard could omit `${REPO:+--repo "$REPO"}` while the test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin REPO on every Step 3 design-pause-save.sh line in the step:3..step:3.5 region (or extend assert_thin_fence to require REPO on all pause-save lines in scoped regions with multiple fences)

### FINDING_2: Mode-flag contract may break existing direct run-step3-review.sh callers
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan’s preference for requiring an explicit `--preview-only`/`--no-preview` mode conflicts with existing direct harness callers that invoke `run-step3-review.sh` without either flag. If implemented strictly, cap and multi-round integration tests can fail before exercising the review behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: For minimum change, keep omitted mode as --no-preview; otherwise add --no-preview to these direct harness calls and document that compatibility break explicitly
  - From Codex-Innovation: Keep no mode as a backward-compatible --no-preview default, or add --no-preview to every direct run-step3-review.sh harness caller in the same plan
  - From Cursor-Pragmatic: In the run-step3-review.sh section, state explicitly: when neither mode flag is passed, behave as --no-preview. Require explicit --preview-only/--no-preview only on SKILL.md fences; optionally add --no-preview to the integration harness call for clarity.
  - From Codex-Pragmatic: Preserve no-flag as --no-preview for backward compatibility, or explicitly add --no-preview to every existing direct harness/CLI caller in the plan
  - From Codex-Requirements: For the minimum-change path, specify that omitted mode remains --no-preview for backward compatibility, while SKILL.md uses explicit --preview-only and --no-preview

### FINDING_3: Preview sentinel handling can bypass or suppress tmpdir allowlist validation
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Moving sentinel ownership into the preview driver risks reading or writing `.step3-entry-plan-printed` before validating `--design-tmpdir`. A stale sentinel can suppress the renderer’s allowlist warning, and a renderer seam or bug can cause the driver to touch the sentinel outside allowed session/tmp roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Before suppressing on an existing sentinel, make --preview-only perform the same missing/invalid and larch_design_tmpdir_validate warning checks, or otherwise preserve the existing allowlist-warning-before-sentinel behavior; add the sentinel-present disallowed-tmpdir case to test-run-step3-review.sh
  - From Codex-Innovation: After renderer output matches the touch string, validate the raw design tmpdir with scripts/lib-design-tmpdir.sh before touch; still call the renderer before validation to preserve live warning behavior
  - From Codex-Requirements: Before any sentinel read/write in --preview-only, require an existing directory that passes larch_design_tmpdir_validate, while still allowing the renderer warning to print live

### FINDING_4: Plan may not deliver the requested Step 3 turn reduction
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The feature request says the preview should become the first action inside `run-step3-review.sh` and remove the separate preview turn, but the plan keeps a separate live preview-only driver fence. That transfers sentinel ownership without necessarily reducing per-entry Step 3 turns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Revise the Phase 2 acceptance to say turn reduction is explicitly deferred, or implement a single driver invocation that streams the preview before review without a second Step 3 fence

### FINDING_5: docs/issue-anchored-plan.md drift target is omitted from the file list
- **Reviewer(s)**: Cursor-dyn-scope-drift, Codex-dyn-scope-drift
- **Severity**: important
- **Concern**: The plan’s drift sweep names `docs/issue-anchored-plan.md`, but the Files to modify/create list omits it. Implementers following the file list may leave the normative wire-format doc describing the old SKILL.md direct `emit-design-plan-preview.sh` preview flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-scope-drift: Add ### UPDATED: docs/issue-anchored-plan.md to the file list (or drop it from step 6) and rewrite lines 189-194 to describe live run-step3-review.sh --preview-only before captured --no-preview, with emit-design-plan-preview.sh as the renderer only
  - From Codex-dyn-scope-drift: Add docs/issue-anchored-plan.md to the UPDATED file list with a minimal note to change the Step 3 preview sentence to the new driver-owned preview flow, or remove it from the drift sweep only if the stale wording is intentionally left unchanged.
