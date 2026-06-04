### FINDING_1: Step 5c still couples rename/admission to PUBLISH_OK
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Requirements, Cursor-dyn-cross-doc-drift, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 5c prose still says rename/admission is gated on `PUBLISH_OK`, contradicting the intended `ADMISSION_READY` / rename-state semantics and potentially blocking or mis-routing `/implement` after a successful rename but failed log publish/scrub.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Edge, Cursor-Requirements, Cursor-dyn-cross-doc-drift: In the same SKILL.md edit, replace item 6 with: rename/admission is driven by ADMISSION_READY/ADMISSION_BLOCK_REASON (and RENAME_*); Step 6 cleanup stays gated on PUBLISH_OK=true when SESSION_ID is non-empty; step-5c sentinel remains PLAN_WRITE_OK-only
  - From Cursor-Pragmatic: Revise item 6: rename/admission follows ADMISSION_READY/ADMISSION_BLOCK_REASON; keep Step 6 cleanup on PUBLISH_OK only

### FINDING_2: Empty SESSION_ID path lacks admission-block state
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: When `SESSION_ID` is empty, rename is skipped but the plan does not define `ADMISSION_READY=false` or a block reason, so final guidance may tell operators to continue even though `/implement` title admission will fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Set ADMISSION_READY=false and ADMISSION_BLOCK_REASON=session-id-missing when SESSION_ID is empty, persist/export it, and update Step 5d/footer/render/tests to say manual/session recovery or rerun is required before /implement.
  - From Codex-Edge: Initialize admission as blocked, e.g. ADMISSION_READY=false and ADMISSION_BLOCK_REASON=session-id-missing, persist/export it, and update Step 5d/render guidance to use the blocked footer for this path.
  - From Codex-Innovation: Set ADMISSION_READY=false and ADMISSION_BLOCK_REASON=session-missing or rename-skipped when SESSION_ID is empty; parse/render it in Step 5d as admission-blocked and add a small test for this edge case.
  - From Codex-Pragmatic: Set ADMISSION_READY=false and ADMISSION_BLOCK_REASON=session-missing when SESSION_ID is empty, persist/export it, and route Step 5d/render to the admission-blocked footer style.

### FINDING_3: Scrub-only failures can omit SCRUB_OK and allow full flush
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Some scrub-only preflight/staging failure paths may return without `SCRUB_OK=false`; if the caller only blocks on explicit false/nonzero, the full publish flush can still run after a failed scrub path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: In --scrub-only mode, make every expected failure path before or during staging/scrub emit SCRUB_OK=false, make design-publish require SCRUB_OK=true exactly before full flush, and add a missing-SCRUB_OK scrub-only test.

### FINDING_4: Structure test checks marker after first publish call instead of full flush
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Test check (25) still orders the marker after the first `design-log-publish.sh` match, which could be the scrub-only call, allowing the full flush to occur after the reentry marker without failing the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Change check (25) to use publish_flush_line (last non --scrub-only call) for marker ordering; keep rename < flush < marker

### FINDING_5: Scrub-failed recovery guidance may dead-end after rename
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: Proposed scrub-failed guidance tells operators to retry Step 5c, but after admission rename the issue may be `[DESIGNED]`, making rerunning `/design` blocked and the recovery instructions unusable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep the minimum-change path: tell operators to fix the scrub/redaction issue and rerun scripts/design-log-publish.sh with the saved DESIGN_TMPDIR/RUN_ID/issue; mention Step 5c retry only if an active orchestrator path truly supports it.

### FINDING_6: Plan scope expands beyond the requested simple rename reorder
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan expands a simple rename reorder into scrub-only plumbing, new admission propagation, render-summary behavior, security docs, and implement-admission docs, adding behavior beyond the stated requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Restore the minimum plan: move only the rename in skills/design/scripts/design-publish.sh, keep existing full-publish scrub behavior, and limit docs/tests to design-publish.md, SKILL.md, test-design-publish.sh, and test-design-structure.sh updates needed for the reorder

### FINDING_7: design-log-publish contract doc would be stale after scrub-only addition
- **Reviewer(s)**: Codex-dyn-cross-doc-drift
- **Severity**: important
- **Concern**: The sibling contract doc would still describe only full-publish `PUBLISH_OK` output and the old test invocation, omitting new scrub-only outputs and side-effect boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-cross-doc-drift: Add scripts/design-log-publish.md as an UPDATED scope entry and document --scrub-only output, side-effect boundary, and harness invocation

### FINDING_8: Scrub-only call needs set +e capture under set -e
- **Reviewer(s)**: Cursor-dyn-arg-threading
- **Severity**: important
- **Concern**: Adding a scrub-only call without a `set +e` capture pattern can abort the driver under `set -e` before `render-final-summary` runs, especially when scrub-only exits nonzero without `SCRUB_OK`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-arg-threading: Wrap scrub-only in the same set +e subshell pattern as full publish; use separate _scrub_out/_scrub_rc

### FINDING_9: RENAME_NOOP missing from live render export contract
- **Reviewer(s)**: Cursor-dyn-result-env-chain, Codex-dyn-result-env-chain
- **Severity**: important
- **Concern**: The proposed render/live-state export list omits `DESIGN_PUBLISH_RENAME_NOOP` even though `RENAME_NOOP` is persisted, parsed, and tested, so render logic may misclassify a no-op rename as a rename failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-result-env-chain: Add export DESIGN_PUBLISH_RENAME_NOOP=true when RENAME_NOOP=true (and teach append_failed_publish_notes to consult it before treating RENAMED=false as failure)
  - From Codex-dyn-result-env-chain: Keep one minimum contract: either add DESIGN_PUBLISH_RENAME_NOOP to the pre-render export and env-first render read list, or remove RENAME_NOOP from render/test expectations and derive no-op from ADMISSION_READY=true plus RENAMED=false.
