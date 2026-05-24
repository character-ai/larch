# review-implement-step5-loop.sh

Internal loop driver for `/implement` Step 5. Runs repeated `review-and-fix.sh` rounds, handles post-round status routing, checks captures, lint-fix repair, bulk-skip gating, and cap enforcement. Emits the `STEP5_REVIEW_STATUS` envelope consumed by `run-step5-review.sh`.

**Primary contract**: `skills/review-and-fix/scripts/review-and-fix.md`

**Callers**: `scripts/run-step5-review.sh` (sources this file and calls `step5_review_loop`)

`step5_parse_kv_tokens` always exits status 0 so `set -e` callers can safely use `v="$(step5_parse_kv_tokens "$line" KEY)"`; a missing key is signaled by empty stdout (after command substitution strips the lone newline), not a non-zero exit. After reading a capture file, `step5_parse_checks_capture_file` requires at least one of `STATUS`, `RELEVANT_CHECKS_OK`, or `RELEVANT_CHECKS_SKIPPED` to have been set; otherwise it logs a required-field line to stderr and fail-closes with `STATUS=fail` and `FAILURE_REASON=malformed-capture`. `step5_parse_lint_capture_file` logs a similar stderr line when `LINT_FIX_STATUS` was never seen but does not force globals—the loop’s `case` on lint status treats empty as the catch-all stall path.
