## Goal
Harden redact_gh_error so failed redaction never re-emits raw gh/jq stderr in ERROR=

## Implementation Plan
Harden redact_gh_error across all sibling scripts so failed redaction never re-emits raw gh/jq stderr in ERROR=.


Already implemented on branch sergey-zhupanov/harden-redact-gh-error-fallback:

1. scripts/tracking-issue-write.sh — changed redact_gh_error from || emit_redaction_failure pattern to status-capture with generic fallback + truncation marker check. Updated ## Security posture comment block.
2. scripts/tracking-issue-read.sh — fixed raw-text fallback (security leak) and added truncation marker check.
3. scripts/clarify-state.sh, clarify-label.sh, clarify-comment-post.sh, plan-block-write.sh, plan-block-read.sh — added truncation marker check to each.
4. scripts/test-tracking-issue-write.sh — added two new fixtures: (a) missing redactor, (b) non-zero redactor exit.
5. scripts/tracking-issue-write.md — updated Security section.
6. SECURITY.md — updated section 108 to document fail-closed contract.

All tests pass. All pre-commit checks pass.

## Test plan
(no test plan section in plan-file)
