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


### FINDING_5: Keep the shared helper signature under the PLR0913 threshold
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed shared helper takes too many direct parameters for the repo's lint baseline, so the new production function is likely to trip PLR0913 and block verification. The problem is the helper shape, not the behavior it implements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Collapse the helper inputs into a small internal request dataclass or context object, keeping the helper signature under the PLR0913 threshold without adding a baseline row.


