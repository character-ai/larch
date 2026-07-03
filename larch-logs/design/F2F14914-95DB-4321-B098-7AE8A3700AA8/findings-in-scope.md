### FINDING_1: Clarify must not upsert the tracking comment before log publish
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Concern**: The clarify flow is performing a tracking-comment upsert before `design log-publish` has succeeded, which can expose a final summary that points at an unpublished or incomplete `larch-logs/design/<run_id>/` tree. The shared concern is that clarify needs exactly one authoritative post-publish summary update, not a pre-publish upsert plus a later repair pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split clarify into one pre-log-publish render with upsert_summary_comment=False, then call tracking-issue upsert-summary from final-summary.md only after log-publish succeeds (or after the best-effort attempt when SESSION_ID is set). Keep a single render; do not upsert inside it.
  - From Codex-Arch: Call the shared helper from clarify with upsert_summary_comment=False before `design log-publish`, and keep the existing Final summary block as the single tracking-comment upsert point. If moving the upsert into Python is intended, include the matching `skills/design/SKILL.md` change that removes or narrows the later Final summary block.

### FINDING_2: Pre-publish render should happen after transcript capture mutates the tmpdir
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The log-publish flow is rendering a summary before `_capture_design_transcript` finishes mutating the temporary design directory, so the committed `final-summary.md` can lag behind the tracking comment and undercount warnings or execution issues. The risk is an authoritative log snapshot being frozen too early in the publish path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Render inside `log_publish_main` after `_capture_design_transcript` succeeds and immediately before `_copy_tree_redacted`, using outcome/issue/repo from caller metadata; keep Step 5c as the sole `upsert_summary_comment=True` pass. Drop redundant caller-side pre-publish renders or treat them as non-authoritative.

### FINDING_3: publish_core must propagate the real mode into the shared helper
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The shared final-summary helper needs the same `mode` value that Step 5c would use, but the `publish_core` path is not clearly sourcing and passing that value before log publish. If `mode` defaults to `N/A` or is omitted, the committed run log can retain an incorrect summary even when later steps repair the tracking comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In `design_publish.py`, source `mode` the same way `_step5c_render_final_summary` does today (`ctx.str_value(config.ENV_MODE)` or `os.environ.get("MODE", "N/A")` when `publish_core` runs in-process) and pass it into every shared-helper call on approved and failed-plan-write paths

### FINDING_4: Preserve the degraded fallback when render fails
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Concern**: The plan wording can be read as if a failed render should leave no `final-summary.md`, but the current helper intentionally writes a degraded fallback body on render failure. Tightening the contract the wrong way would remove a non-gating fallback and make hard failures less observable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Revise the helper spec to: unlink only clears stale pre-render files; on failure keep today's non-gating degraded-fallback behavior (or explicitly delegate to existing `render_final_summary_main` semantics without post-failure deletion).

### FINDING_5: Keep the shared helper signature under the PLR0913 threshold
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed shared helper takes too many direct parameters for the repo's lint baseline, so the new production function is likely to trip PLR0913 and block verification. The problem is the helper shape, not the behavior it implements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Collapse the helper inputs into a small internal request dataclass or context object, keeping the helper signature under the PLR0913 threshold without adding a baseline row.

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_pause.py:219-238
- **Concern**: [SCOPE-REDUCTION] Drop pause final-summary rendering from this fix. Scenario: The binding issue is terminal /design final report output. Pause snapshots are non-terminal; adding a pause outcome, upsert-suppression wiring, and pause-only tests expands scope beyond restoring terminal logs and tracking comments.
- **Proposed resolution**: Limit the change to publish_core, clarify, and Step 5c delegation. Leave pause log-publish unchanged in this PR; file a follow-up if pause snapshots need final-summary.md.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_pause.py:219-238
- **Concern**: [SCOPE-REDUCTION] Pause snapshot final-summary rendering is outside the terminal final-report bug. Scenario: [DESIGNING] pause is a non-terminal checkpoint. It does not restore the missing terminal chat/report output operators reported, but it adds a new pause outcome, upsert-suppression branching, pause-save tests, and committed pause artifacts beyond the minimum fix.
- **Proposed resolution**: Limit the first fix to terminal paths (`design_publish.py` approved/failed-plan-write, `clarify.py`, Step 5c). Defer pause `final-summary.md` work to a follow-up issue unless pause snapshots are explicitly in scope.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_pause.py:219-238
- **Concern**: [SCOPE-REDUCTION] Drop pause-save final-summary rendering from this fix. Scenario: Pause is a non-terminal checkpoint; the binding bug is missing terminal final report output and enriched committed logs on approved/failed-plan-write/clarify paths. Pause work adds a new outcome token, upsert-suppression branching, helper wiring, and pause-only tests beyond restoring terminal behavior.
- **Proposed resolution**: Defer `design_pause.py` helper integration and `test_design_pause.py` additions; keep the shared helper plus `design_publish.py`, `clarify.py`, and Step 5c delegation as the minimum fix for the reported regression.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_pause.py:219-238
- **Concern**: [SCOPE-REDUCTION] Pause snapshot final-summary rendering exceeds the binding bug scope. Scenario: The issue is terminal `/design` final-report output and tracking-comment upsert. Pause is a non-terminal checkpoint; adding pause outcome, upsert suppression, and pause-specific tests expands the fix without restoring the reported regression
- **Proposed resolution**: Drop `design_pause.py` helper wiring, the new pause outcome token, and `test_design_pause.py` additions from this change. Limit pre-log-publish rendering to terminal callers (`publish_core`, clarify publish)

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:141-143
- **Concern**: [SCOPE-REDUCTION] Testing strategy asks for full `make py-test` and `make py-lint`, which conflicts with the repo constraint to lint/test only changed files.. Scenario: The plan expands validation beyond the minimum-change contract, while CI owns the full sweep.
- **Proposed resolution**: Drop the full-sweep commands. Keep the listed focused pytest files and changed-file lint only.
