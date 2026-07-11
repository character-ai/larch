### FINDING_1: Step 5c routes publish rc 5 through the configuration-error early-exit guard
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Step 5c still routes publish rc 5 through the early-exit guard meant for configuration errors. The guard `publish_rc == 2 or publish_rc not in {0, 1, 3, 4}` treats rc 5 like rc 2: it skips `_step5c_safe_publish_env`, writes status with empty `plan_write_ok`, stages terminal state from a one-line failure log, and returns before copying stderr tails or reading `.design-publish-result.env`. That matches the #6819 failure mode where post-plan progress existed on disk but the auto-report saw stale rc-4 refusal state and empty diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Restructure `step5c_core` so rc 5 follows a dedicated terminal-failure path: persist stdout/stderr tails under `DESIGN_TMPDIR`, read the current publish result env, render `design-publish-tail.failure.log` from structured state, write enriched `.design-step5c-status.env`, then call terminal staging. Keep rc 2 on the early-exit branch or give it an equivalent minimal path.


### FINDING_2: Publish-tail classification is not wired into the generic `/design` profile
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Structured publish-tail classification is not wired into the generic profile `/design` actually uses. `design_terminal.py` calls stall recovery with `--profile generic --artifact-prefix design-failure`, which always enters `_classify_generic_from_terminal_state`. That function hardcodes `resume_hint = "none"` and classifies only via `_classify_text` on failure-detail text. Adding a helper elsewhere in `_classify.py` without changing this entrypoint leaves publish-tail rc-5 failures `unrecoverable` with `MATCHED_CLASSIFIER_PATTERN=fallback` even after terminal state carries progress and identity fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `_classify_generic_from_terminal_state`, branch on validated terminal-state tokens for `TRIGGER=publish-tail-failed` and `EXIT_CODE=5` (plus copied publish-progress fields) to the new structured classifier before `_classify_text`. Emit `FAILURE_CLASS=recoverable`, the complete-post-plan resume hint, and the named publish-tail pattern only when validated checkpoint evidence supports it; otherwise keep the existing fallback path.


### FINDING_4: Stale publish result env can survive a fresh initialization failure
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Fresh initialization failure can leave the previous attempt's result env eligible. The proposed initialization may fail before replacing an existing result env. Step 5c then handles the exception as rc 5 but can read stale PLAN_WRITE_OK, progress, branch, or PR values and misclassify the new attempt as recoverable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Have Step 5c invalidate the prior result env before invocation and fail without reading it if invalidation fails. Write each checkpoint atomically.


