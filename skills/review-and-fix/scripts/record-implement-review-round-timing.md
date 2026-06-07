# record-implement-review-round-timing.sh

Deferred `/implement` Step 5 review-round timing helper. The Step 5 prompt-side handoff paths call this after main-agent adjudication/application and captured checks/lint, but before `commit-review-fixes.sh`, so a round row stays inside the Step 5 interval.

Args: `--implement-tmpdir PATH --round N --start-s S --end-s E`.

The helper canonicalizes the tmpdir, binds `LARCH_TIMING_LEDGER` to `$IMPLEMENT_TMPDIR/timing-ledger.tsv`, counts round-local accepted/rejected findings from `round-N/review-tally.env` when present, falls back to accepted/rejected artifacts, then emits `timing-ledger.sh record-round --skill implement --step "Step 5 — code review"`. Failures are warn-only for callers. `LARCH_TIMING_SKILL=implement` is set via `export` on the line immediately preceding the `timing-ledger.sh record-round` call (export-or-same-line relaxation; covered by the A1 scanner in `scripts/test-implement-structure.sh`). The idempotency pre-check uses full-tuple fingerprinting (round + start-s + end-s), matching the post-call verification block.

Harness: covered by `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh` for helper-specific counting, idempotency, foreign-row isolation, stall-style deferred emit, and record-before-Step-7 ordering cases, plus `scripts/test-timing-ledger.sh` / `scripts/test-timing-report.sh` for shared ledger and reporting behavior.
