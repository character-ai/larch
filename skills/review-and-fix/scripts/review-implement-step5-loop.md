# review-implement-step5-loop.sh

Internal loop driver for `/implement` Step 5. Runs repeated `review-and-fix.sh` rounds, handles post-round status routing, checks captures, lint-fix repair, bulk-skip gating, and cap enforcement. Emits the `STEP5_REVIEW_STATUS` envelope consumed by `run-step5-review.sh`.

**Primary contract**: `skills/review-and-fix/scripts/review-and-fix.md`

**Callers**: `scripts/run-step5-review.sh` (sources this file and calls `step5_review_loop`)
