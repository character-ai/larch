## Goal
Isolate the timing ledger in scripts/test-launch-review.sh so IMPLEMENT_TMPDIR='' launcher invocations don't contaminate the global timing ledger with test stub records.

## Implementation Plan
Add `export LARCH_TIMING_LEDGER="$TMPDIR/timing-ledger.tsv"` after line 63 in scripts/test-launch-review.sh (after the TMPDIR trap). This mirrors commit 2cfa469's fix to test-cursor-implementer.sh and test-gemini-implementer.sh. Update sibling scripts/test-launch-review.md if it mentions timing behavior.

## Test plan
Run `bash scripts/test-launch-review.sh` and verify codex section passes.
