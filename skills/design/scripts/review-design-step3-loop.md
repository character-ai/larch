# review-design-step3-loop.sh

## Purpose

Sourced Step 3 loop controller for `/design` plan-review rounds.

## Primary callers

- `skills/design/scripts/design-step3-review.sh` invokes this loop through `python3 python/cli.py plan-review run --mode loop`.
- `python/plan_review.py` embeds this file in `_LEGACY_ASSETS` so `python3 python/cli.py plan-review run --mode loop` materializes the live runtime copy.

## Invariants

- `.step3-review-result.env` is per-round handoff state. It may exist between automatic rounds and is not a terminal hook-release sentinel.
- `.completed/step-3` and `.completed/step-3.5` are pause and Gate B milestones. They are written only when the loop emits a terminal Step 3 envelope.
- `.completed/step-3-terminal` is the hook-release and recovery sentinel. `step3_loop_write_terminal_step3()` writes it only after `step3_loop_persist_envelope()` successfully persists `.step3-review-result.env`.
- `.step3-terminal-persisted-this-run` is the current-pass sidecar used by `design-step3-review.sh` trap fallback. A stale result env alone must not mint `step-3-terminal`.
- Automatic continuation clears `.step3-review-result.env` before incrementing to the next round so stale per-round state cannot satisfy prompt-side recovery waiters.
- The per-round body capture (`.step3-round-body.<rand>`) is created with `mktemp`, written by `run_step3_round_body`, then relayed via `cat`. If `mktemp` fails, or the capture vanishes mid-round because DESIGN_TMPDIR scratch was cleaned by a sub-step, the loop emits a clear warning instead of a raw `cat: No such file` error so tally-error failures stay diagnosable (#4431). The normalized result env, not the capture, remains the authoritative loop status.
- `step3_loop_persist_envelope()` remains the only writer for the normalized Step 3 result env. Successful persist orders durability before recovery release: result env write succeeds, then `step-3-terminal` and the persist sidecar are written. Terminal paths may have written `step-3` / `step-3.5` earlier via `step3_loop_write_completed_step3()`.
- Existing kill behavior lives outside Step 6 cleanup. `design-step3-review.sh` kills background processes from its EXIT trap after the loop process returns, and `python/finalize.py` kills before tmpdir deletion on the finalize path. Step 6 `cleanup-tmpdir` remains a plain cleanup helper.

## Harness

Covered by `scripts/test-design-multi-round-integration.sh`, `python/test_plan_review.py`, and `make test-review-design-step3-loop`.

## Edit-in-sync

When this source changes, regenerate the matching gzip entry in `python/plan_review.py` and keep the decoded-blob parity assertion in `python/test_plan_review.py` passing.
