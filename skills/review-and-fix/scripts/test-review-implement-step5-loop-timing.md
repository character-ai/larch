# test-review-implement-step5-loop-timing.sh

Focused timing regression harness for `review-implement-step5-loop.sh` helpers and terminal Step 5 branches.

It pins in-loop round timing rows, deferred prompt-side handoff timing, lint-fix `main-agent-required` single-writer behavior, and the `step-5-resume.sh --record-only` no-duplicate guard.

## Caller

Run with `bash skills/review-and-fix/scripts/test-review-implement-step5-loop-timing.sh`.

## Edit-in-sync

Update this file with `review-implement-step5-loop.sh`, `record-implement-review-round-timing.sh`, and `skills/implement/scripts/step-5-resume.sh` when timing row ownership changes.
