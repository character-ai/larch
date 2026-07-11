### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step5c.py:582-606
- **Concern**: Step 5c still routes publish rc 5 through the early-exit guard meant for configuration errors. Scenario: The guard `publish_rc == 2 or publish_rc not in {0, 1, 3, 4}` treats rc 5 like rc 2: it skips `_step5c_safe_publish_env`, writes status with empty `plan_write_ok`, stages terminal state from a one-line failure log, and returns before copying stderr tails or reading `.design-publish-result.env`. That matches the #6819 failure mode where post-plan progress existed on disk but the auto-report saw stale rc-4 refusal state and empty diagnostics.
- **Proposed resolution**: Restructure `step5c_core` so rc 5 follows a dedicated terminal-failure path: persist stdout/stderr tails under `DESIGN_TMPDIR`, read the current publish result env, render `design-publish-tail.failure.log` from structured state, write enriched `.design-step5c-status.env`, then call terminal staging. Keep rc 2 on the early-exit branch or give it an equivalent minimal path.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:321-371
- **Concern**: Structured publish-tail classification is not wired into the generic profile `/design` actually uses. Scenario: `design_terminal.py` calls stall recovery with `--profile generic --artifact-prefix design-failure`, which always enters `_classify_generic_from_terminal_state`. That function hardcodes `resume_hint = "none"` and classifies only via `_classify_text` on failure-detail text. Adding a helper elsewhere in `_classify.py` without changing this entrypoint leaves publish-tail rc-5 failures `unrecoverable` with `MATCHED_CLASSIFIER_PATTERN=fallback` even after terminal state carries progress and identity fields.
- **Proposed resolution**: In `_classify_generic_from_terminal_state`, branch on validated terminal-state tokens for `TRIGGER=publish-tail-failed` and `EXIT_CODE=5` (plus copied publish-progress fields) to the new structured classifier before `_classify_text`. Emit `FAILURE_CLASS=recoverable`, the complete-post-plan resume hint, and the named publish-tail pattern only when validated checkpoint evidence supports it; otherwise keep the existing fallback path.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:1198-1222
- **Concern**: 1. [correctness] The plan records rename progress but does not require checking the tracking-issue rename subprocess result or treating an unsuccessful rename as a failed publish tail.. Scenario: `tracking-issue rename` can return nonzero while emitting no validated `RENAMED` value; the code then continues to log publication and may return success, leaving the required issue rename incomplete and preventing the new terminal diagnostics and recoverability classification from running.
- **Proposed resolution**: Check `rename.returncode` and validated rename evidence before continuing. Persist an explicit attempted/failed rename state, capture its stderr, and return rc 5 or otherwise surface the failure through the planned terminal reporting path.

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:57-62
- **Concern**: 1. Fresh initialization failure can leave the previous attempt's result env eligible. Scenario: The proposed initialization may fail before replacing an existing result env. Step 5c then handles the exception as rc 5 but can read stale PLAN_WRITE_OK, progress, branch, or PR values and misclassify the new attempt as recoverable.
- **Proposed resolution**: Have Step 5c invalidate the prior result env before invocation and fail without reading it if invalidation fails. Write each checkpoint atomically.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_publish.py:57-62,836,1242
- **Concern**: 2. Global OSError propagation can break the existing rc-3 stdout fallback. Scenario: A final result-env write can fail after all publish work succeeds. Changing _write_result_env to raise globally would map this existing rc-3 case to terminal rc 5, aborting and reporting a successfully published design instead of using Step 5c's stdout fallback.
- **Proposed resolution**: Preserve the rc-3 return contract for final result writes. Propagate checkpoint failures only where stale progress makes continuation unsafe, or catch write exceptions at final-write call sites and return 3.
