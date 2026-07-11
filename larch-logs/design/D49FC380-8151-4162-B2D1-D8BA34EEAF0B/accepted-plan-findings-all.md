### FINDING_1: Terminal-state URL and branch fields are rejected by raw-value validation
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Diagnostic Egress Auditor
- **Severity**: major
- **Concern**: The proposed terminal-state PR URL and branch fields are checked by `_reject_rawish_terminal_value` before their dedicated validators. Values such as `PR_URL=https://github.com/...` therefore invalidate the entire terminal state, causing fallback reporting and preventing recoverable classification from consuming the progress and identity data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Exempt the PR-URL terminal-state key from _reject_rawish_terminal_value like FAILURE_DETAIL_LOG is, or store only the PR number (bounded integer) in terminal state and reconstruct the URL at render time; state the chosen contract explicitly in the _validate.py step
  - From Cursor-dyn-Diagnostic Egress Auditor: Exempt the new URL and branch keys from the blanket _reject_rawish_terminal_value pass, or validate them only through dedicated validators in _terminal_state_value_valid.


### FINDING_2: The new publish-tail classifier pattern is not in the safe pattern allowlist
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The generic classifier renders `MATCHED_CLASSIFIER_PATTERN` through `_safe_matched_pattern_value`, whose fixed allowlist does not include the proposed publish-tail rc-5 pattern. The classifier will therefore emit `redacted` instead of the named pattern, defeating the deliverable and its tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the new publish-tail pattern token(s) to the _safe_matched_pattern_value allowlist in the _tokens.py step so the classifier emits the named pattern instead of "redacted"


### FINDING_9: Nested publish subprocess stderr is not preserved in the failure detail
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Capturing only Step 5c’s outer stderr does not preserve stderr emitted by nested `tracking-issue rename` and `design log-publish` subprocesses. Returned rc-5 paths can therefore produce an empty outer stderr capture despite the decisive diagnostic being available in a child process.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: At each nested subprocess failure, persist a bounded, redaction-eligible phase stderr artifact or emit its bounded content into the Step 5c diagnostic stream. Include rename and log-publish stderr in the lifecycle tests, including returned rc-5 cases.


### FINDING_10: PLAN_WRITE_OK is insufficient evidence for the rename-and-log-flush resume hint
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Required post-plan phases such as difficulty-label sync, rating persistence, and diagram upsert can still be incomplete after `PLAN_WRITE_OK=true`. Emitting a hint that performs only rename and log flush can therefore skip unfinished required work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use a resume hint that reruns the full post-plan publish tail, or add a validated checkpoint after all required pre-rename phases and reserve `design-rename-log-flush` for that checkpoint
  - From Codex-Requirements: Track checkpoints for all required post-plan phases, or use a resume operation that safely reruns the complete post-plan publish tail instead of only rename and log flush.


### FINDING_14:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan.txt:70-76,145-159
- **Concern**: [SCOPE-REDUCTION] The plan makes salvage reconciliation, GitHub commenting, issue closing, and remote close verification a mandatory part of this diagnostics fix. Scenario: Core diagnostics, structured classification, accurate recoverability reporting, and flushed evidence work without mutating or closing a later report issue; the added reconciliation path introduces substantial GitHub state, idempotency, and failure handling that is explicitly optional in the issue scope
- **Proposed resolution**: Keep terminal diagnostics and recoverability reporting in this change, but defer the comment/close reconciliation flow and its related tests to a tracked follow-up unless the originating issue is amended to require it


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


