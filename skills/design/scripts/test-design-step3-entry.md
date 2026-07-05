# test-design-step3-entry.sh

## Purpose

Regression harness for `design-step3-entry.sh`.

## Primary callers

- `Makefile` target `test-design-step3-entry`

## Invariants

- Verifies Step 3 scope-anchor materialization from a stripped issue body.
- Verifies a stripped issue body that becomes empty does not fall back to `feature-description.txt`.
- Verifies `--reentry` resets `oos-aggregate-pool.md`.

## Harness

Run with `make test-design-step3-entry`.

## Edit in sync

Keep this file aligned with `test-design-step3-entry.sh` cases and the `design-step3-entry.sh` contract.
