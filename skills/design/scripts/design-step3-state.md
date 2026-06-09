# design-step3-state.sh

Shared `/design` Step 3 sentinel mutation helper.

## Purpose

Centralizes state transitions that must be safe across pause/resume and direct Step 3 re-entry:

- `--gate-b-bypass` writes `.completed/step-3` and `.completed/step-3.5` when Step 3 skips Gate B.
- `--direct-review-entry` consumes `.step3-reentry`, clears stale downstream sentinels, restores the direct-review bypass package, clears cumulative review artifacts, and removes settled lower-round loop phase/snapshot files.
- `--direct-review-pause-hygiene` performs the same sentinel hygiene without consuming `.step3-reentry`.
- `--auto-continuation-entry` clears unsafe downstream sentinels before the script-internal Step 3 loop advances to another round and removes settled lower-round `.step3-round-*.phase` / `plan-pre-apply-round-*.txt` state.

## Loop-state cleanup

`review-round-count.txt` records the last consumed review round. This helper removes `.step3-round-N.phase` and `plan-pre-apply-round-N.txt` for rounds `N <= review-round-count.txt`, ignoring symlinks and malformed names, so stale phase markers cannot mis-route a fresh `--mode loop` entry at `count + 1`.

## Harness

`skills/design/scripts/test-design-step3-state.sh` covers Gate-B bypass, direct-review re-entry, pause hygiene, auto-continuation cleanup, and settled lower-round loop-state cleanup.
