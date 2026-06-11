# test-record-plan-review-round-timing.sh

Offline harness for `record-plan-review-round-timing.sh`. It verifies accepted/rejected counts, accepted-only OOS tally parsing from `voting-tally.md`, ignored bare rejected headings, idempotent deferred emission, and zero-count round rows. Negative-duration clamping is covered by `python/test_timing.py`.
