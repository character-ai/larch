# snapshot-plan-round.sh

Write-once plan snapshots and `plan-review-round-cursor.txt` for the HARD-only assessor (`assessor.md`).

Subcommands: `write-original`, `write-after`, `read-cursor`, `write-cursor`, `revert-round`. Cursor file must be a single positive decimal integer ≥ 1; malformed values default to `1` with stderr warning.

## `revert-round --round N`

Rolls back round `N`'s applied findings after a Step 3.6 assessor WORSE-majority verdict when the operator picks **Revert** (see `assessor.md` §Operator UX). Restores `plan.txt` to the pre-round snapshot — `plan-after-round-<N-1>.txt` for `N > 1`, or `plan.txt-original` for `N == 1` (the round-1 baseline; present because the assessor is HARD-only and Step 2b writes `plan.txt-original` write-once) — drops round `N`'s post-Gate-B snapshot `plan-after-round-<N>.txt`, and rolls the cursor + counter back (`plan-review-round-cursor.txt = N`, `review-round-count.txt = N-1`), mirroring the driver's write-after-failed rollback so a later Gate C re-run redoes round `N` on the reverted plan.

Emits `REVERT_STATUS=ok`, `RESTORED_FROM=<basename>`, `CURSOR=N`, `REVIEW_ROUND_COUNT=N-1` on FD 3. Exit `2` when `--round` is missing/non-positive or the restore source snapshot is absent (orchestrator falls through to keep the applied plan, i.e. Continue semantics); exit `1` on copy-back failure.
