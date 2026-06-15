# review-design-step3-loop.sh

## Purpose

Sourced Step 3 loop controller for `/design` plan-review rounds.

## Primary callers

- `skills/design/scripts/run-step3-review.sh` sources this file after defining `run_step3_round_body`.
- `python/plan_review.py` embeds this file in `_LEGACY_ASSETS` so `python3 python/cli.py plan-review run --mode loop` materializes the live runtime copy.

## Invariants

- `.step3-review-result.env` is per-round handoff state. It may exist between automatic rounds and is not a terminal loop sentinel.
- `.completed/step-3` is the terminal loop sentinel. It is written only when the loop emits a terminal Step 3 envelope.
- Automatic continuation clears `.step3-review-result.env` before incrementing to the next round so stale per-round state cannot satisfy prompt-side recovery waiters.
- `step3_loop_persist_envelope()` remains the only writer for the normalized Step 3 result env.
- Existing kill behavior lives outside Step 6 cleanup. `design-step3-review.sh` kills background processes from its EXIT trap after the loop process returns, and `python/finalize.py` kills before tmpdir deletion on the finalize path. Step 6 `cleanup-tmpdir` remains a plain cleanup helper.

## Harness

Covered by `scripts/test-design-multi-round-integration.sh`, `python/test_plan_review.py`, and `make test-review-design-step3-loop`.

## Edit-in-sync

When this source changes, regenerate the matching gzip entry in `python/plan_review.py` and keep the decoded-blob parity assertion in `python/test_plan_review.py` passing.
