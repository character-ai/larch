### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/clarify.py:1082-1206
- **Concern**: Clarify pre-log-publish render must not upsert the tracking comment. Scenario: Plan renders cancelled-clarify/failed-clarify with upsert_summary_comment=True before design log-publish. Step 5c keeps upsert after publish. If log-publish fails, the issue comment can show a final summary pointing at larch-logs/design/<run_id>/ before that tree is committed.
- **Proposed resolution**: Split clarify into one pre-log-publish render with upsert_summary_comment=False, then call tracking-issue upsert-summary from final-summary.md only after log-publish succeeds (or after the best-effort attempt when SESSION_ID is set). Keep a single render; do not upsert inside it.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/clarify.py:1089-1098; skills/design/SKILL.md:149-154
- **Concern**: Clarify pre-log-publish render keeps two tracking-comment upsert points. Scenario: The plan sets clarify's pre-log-publish helper call to upsert the `larch:final-summary` comment, but `skills/design/SKILL.md` still runs the existing Final summary block after the clarify publish fence. That leaves a premature upsert before `design log-publish` outcome is known, then a second upsert afterward. On log-publish failure, the issue comment can show `cancelled-clarify` until the later block repairs it, and an interrupted run can leave the wrong terminal comment.
- **Proposed resolution**: Call the shared helper from clarify with `upsert_summary_comment=False` before `design log-publish`, and keep the existing Final summary block as the single tracking-comment upsert point. If moving the upsert into Python is intended, include the matching `skills/design/SKILL.md` change that removes or narrows the later Final summary block.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_log_publish_flow.py:467-474
- **Concern**: Caller-side pre-log-publish render runs before transcript capture mutates the tmpdir. Scenario: `log_publish_main` calls `_capture_design_transcript` after callers render, and capture can append to `execution-issues.md` (and add transcript artifacts) before `_publish_design_logs` copies the tree. A render in `publish_core`/`clarify`/`pause` before `design log-publish` freezes `final-summary.md` too early; Step 5c's later render upserts a richer body to the tracking comment only, so committed logs can undercount warnings/exec issues relative to the comment.
- **Proposed resolution**: Render inside `log_publish_main` after `_capture_design_transcript` succeeds and immediately before `_copy_tree_redacted`, using outcome/issue/repo from caller metadata; keep Step 5c as the sole `upsert_summary_comment=True` pass. Drop redundant caller-side pre-publish renders or treat them as non-authoritative.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:506-514
- **Concern**: [ALREADY_ADDRESSED] Align render-failure file contract with `render_final_summary_main`. Scenario: The plan says unlink-before-render means a failed render leaves no `final-summary.md`, but `render_final_summary_main` always writes a degraded fallback body when `invoke_render` fails. An implementer following the plan literally may delete that fallback and leave log-publish with no summary on hard failures.
- **Proposed resolution**: Revise the helper spec to: unlink only clears stale pre-render files; on failure keep today's non-gating degraded-fallback behavior (or explicitly delegate to existing `render_final_summary_main` semantics without post-failure deletion).

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/design/design_summary.py:421
- **Concern**: New shared helper signature will trip the complexity baseline. Scenario: Plan requires a helper accepting design_tmpdir, outcome, mode, issue_number, session_id, repo, stdout log path, plus upsert_summary_comment. make py-lint runs the PLR0913 complexity-baseline audit, so this new production function creates a new too-many-arguments finding and blocks verification.
- **Proposed resolution**: Collapse the helper inputs into a small internal request dataclass or context object, keeping the helper signature under the PLR0913 threshold without adding a baseline row.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:824-986
- **Concern**: `publish_core` must pass the same `mode` value Step 5c uses into the shared helper before log publish. Scenario: The helper contract includes `mode`, but the `publish_core` section only names outcome and upsert flags. The pre-log-publish render is what log publish copies into the committed run log, so a missing or default `N/A` mode there persists in `larch-logs/design/<RUN_ID>/final-summary.md` even when Step 5c later upserts a summary with real mode flags
- **Proposed resolution**: In `design_publish.py`, source `mode` the same way `_step5c_render_final_summary` does today (`ctx.str_value(config.ENV_MODE)` or `os.environ.get("MODE", "N/A")` when `publish_core` runs in-process) and pass it into every shared-helper call on approved and failed-plan-write paths
